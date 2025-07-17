from abc import ABC
from dataclasses import dataclass
from typing import Callable, Union, Optional

from .ctx import Ctx
from .node import Cursor
from .errors import SemanticError

# Declaramos nossa classe base num módulo separado para esconder um pouco de
# Python relativamente avançado de quem não se interessar pelo assunto.
#
# A classe Node implementa um método `pretty` que imprime as árvores de forma
# legível. Também possui funcionalidades para navegar na árvore usando cursores
# e métodos de visitação.
from .node import Node


#
# TIPOS BÁSICOS
#

# Tipos de valores que podem aparecer durante a execução do programa
Value = bool | str | float | None | Callable


class Expr(Node, ABC):
    """
    Classe base para expressões.

    Expressões são nós que podem ser avaliados para produzir um valor.
    Também podem ser atribuídos a variáveis, passados como argumentos para
    funções, etc.
    """


class Stmt(Node, ABC):
    """
    Classe base para comandos.

    Comandos são associdos a construtos sintáticos que alteram o fluxo de
    execução do código ou declaram elementos como classes, funções, etc.
    """


@dataclass
class Program(Node):
    """
    Representa um programa.

    Um programa é uma lista de comandos.
    """

    stmts: list[Stmt]

    def eval(self, ctx: Ctx):
        for stmt in self.stmts:
            stmt.eval(ctx)


#
# EXPRESSÕES
#
@dataclass
class BinOp(Expr):
    """
    Uma operação infixa com dois operandos.

    Ex.: x + y, 2 * x, 3.14 > 3 and 3.14 < 4
    """

    left: Expr
    right: Expr
    op: Callable[[Value, Value], Value]

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        right_value = self.right.eval(ctx)
        return self.op(left_value, right_value)


@dataclass
class Var(Expr):
    """
    Uma variável no código

    Ex.: x, y, z
    """

    name: str

    def validate_self(self, cursor: Cursor):
        """Valida que o nome da variável não é uma palavra reservada"""
        if self.name in RESERVED_WORDS:
            raise SemanticError("nome inválido", token=self.name)

    def eval(self, ctx: Ctx):
        try:
            return ctx[self.name]
        except KeyError:
            raise NameError(f"variável {self.name} não existe!")


@dataclass
class Literal(Expr):
    """
    Representa valores literais no código, ex.: strings, booleanos,
    números, etc.

    Ex.: "Hello, world!", 42, 3.14, true, nil
    """

    value: Value

    def eval(self, ctx: Ctx):
        return self.value


@dataclass
class And(Expr):
    """
    Uma operação infixa com dois operandos.

    Ex.: x and y
    """
    left: Expr
    right: Expr

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        if is_falsey(left_value):
            return left_value
        return self.right.eval(ctx)


@dataclass
class Or(Expr):
    """
    Uma operação infixa com dois operandos.
    Ex.: x or y
    """
    left: Expr
    right: Expr

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        if not is_falsey(left_value):
            return left_value
        return self.right.eval(ctx)


@dataclass
class UnaryOp(Expr):
    """
    Uma operação prefixa com um operando.

    Ex.: -x, !x
    """
    expr: Expr
    op: Callable[[Value], Value]

    def eval(self, ctx: Ctx):
        expr_value = self.expr.eval(ctx)
        return self.op(expr_value)


@dataclass
class Call(Expr):
    """
    Uma chamada de função.

    Ex.: fat(42)
    """

    callee: Var
    params: list[Expr] | None

    def eval(self, ctx: Ctx):
        func = self._eval_callee(ctx)
    
        args = [param.eval(ctx) for param in (self.params or []) if param is not None]
        
        return func(*args)

    def _eval_callee(self, ctx):
        callee = self.callee
        if isinstance(callee, Var):
            val = ctx[callee.name]
            # print(f"Resolvido Var: {callee.name} -> {val} ({type(val)})")  # COMENTE OU REMOVA
            return val
        elif isinstance(callee, Getattr):
            obj = callee.attr_main.eval(ctx)
            # Usar get() para LoxInstance, getattr para outros objetos
            from .runtime import LoxInstance
            if isinstance(obj, LoxInstance):
                attr = obj.get(callee.attr)
            else:
                attr = getattr(obj, callee.attr)
            # print(f"Getattr: {obj}.{callee.attr} -> {attr} ({type(attr)})")  # COMENTE OU REMOVA
            return attr
        elif isinstance(callee, Call):
            val = callee.eval(ctx)
            # print(f"Call retornou: {val} ({type(val)})")  # COMENTE OU REMOVA
            return val
        else:
            raise RuntimeError(f"Unsupported callee type: {type(callee)}")

@dataclass
class This(Expr):
    """
    Acesso ao `this`.

    Ex.: this
    """

    def validate_self(self, cursor: Cursor):
        """Valida se this está dentro de uma classe"""
        # Procurar por Class na árvore de contexto
        current = cursor.parent_cursor
        while current is not None:
            node = current.node
            if isinstance(node, Class):
                # Verificar se estamos dentro de um método da classe
                method_cursor = cursor.parent_cursor
                while method_cursor is not None and method_cursor != current:
                    if isinstance(method_cursor.node, Function):
                        return  # This dentro de método - válido
                    method_cursor = method_cursor.parent_cursor
                # This diretamente na classe (fora de método) - inválido
                break
            current = current.parent_cursor
        
        raise SemanticError("Can't use 'this' outside of a class.", token="this")
    
    def eval(self, ctx: Ctx):
        # This should resolve to the this object injected in the context
        try:
            return ctx["this"]
        except KeyError:
            raise RuntimeError("this not found in context")


@dataclass
class Super(Expr):
    """
    Acesso a method ou atributo da superclasse.

    Ex.: super.x
    """

    def validate_self(self, cursor: Cursor):
        """Valida se super está dentro de uma classe com superclasse"""
        # Procurar por Class na árvore de contexto
        current = cursor.parent_cursor
        enclosing_class = None
        
        while current is not None:
            node = current.node
            if isinstance(node, Class):
                enclosing_class = node
                break
            current = current.parent_cursor
        
        if enclosing_class is None:
            raise SemanticError("Can't use 'super' outside of a class.", token="super")
        
        if enclosing_class.superclass is None:
            raise SemanticError("Can't use 'super' in a class with no superclass.", token="super")
        
        # Verificar se estamos dentro de um método da classe
        method_cursor = cursor.parent_cursor
        while method_cursor is not None and method_cursor.node != enclosing_class:
            if isinstance(method_cursor.node, Function):
                return  # Super dentro de método - válido
            method_cursor = method_cursor.parent_cursor
    
    def eval(self, ctx: Ctx):
        # Super should resolve to the super object injected in the context
        try:
            return ctx["super"]
        except KeyError:
            raise RuntimeError("super not found in context")


@dataclass
class Assign(Expr):
    """
    Atribuição de variável.

    Ex.: x = 42
    """

    name: str
    value: Expr

    def eval(self, ctx: Ctx):
        key = self.name
        value = self.value.eval(ctx)
        ctx[key] = value
        return value


@dataclass
class Getattr(Expr):
    """
    Acesso a atributo de um objeto.

    Ex.: x.y
    """
    attr_main: Expr  
    attr: str
    subattr:  Union[str, Expr,None]

    def eval(self, ctx: Ctx):

        obj = self.attr_main.eval(ctx)

        # Primeiro nível: getattr(obj, attr) - usar get() para LoxInstance
        from .runtime import LoxInstance
        if isinstance(obj, LoxInstance):
            value = obj.get(self.attr)
        else:
            value = getattr(obj, self.attr)

        # Encadeamento: getattr(obj.attr, subattr)
        if self.subattr is not None:
            if isinstance(self.subattr, Var):
                subattr_name = self.subattr.name
            elif isinstance(self.subattr, Expr):
                subattr_name = self.subattr.eval(ctx)
            else:
                subattr_name = self.subattr

            if isinstance(value, LoxInstance):
                value = value.get(subattr_name)
            else:
                value = getattr(value, subattr_name)

        return value


@dataclass
class Setattr(Expr):
    """
    Atribuição de atributo de um objeto.

    Ex.: x.y = 42
    """

    target: Expr
    attr: str
    value: Expr

    def eval(self, ctx: Ctx):
        target = self.target.eval(ctx)
        value = self.value.eval(ctx)
        
        # Usar set() para LoxInstance, erro para outros tipos
        from .runtime import LoxInstance, LoxClass, LoxError
        if isinstance(target, LoxInstance):
            target.set(self.attr, value)
        elif isinstance(target, (LoxClass, LoxFunction)):  # LoxFunction from ast.py
            raise LoxError("Only instances have fields.")
        else:
            # Para outros tipos Python, use setattr (backward compatibility)
            setattr(target, self.attr, value)
        return value


#
# COMANDOS
#
@dataclass
class Print(Stmt):
    """
    Representa uma instrução de impressão.

    Ex.: print "Hello, world!";
    """

    expr: Expr

    def eval(self, ctx: Ctx):
        from . import runtime
        value = self.expr.eval(ctx)
        runtime.print(value)


@dataclass
class Return(Stmt):
    """
    Representa uma instrução de retorno.

    Ex.: return x;
    """

    expr: Expr

    def validate_self(self, cursor: Cursor):
        """Valida se return está dentro de uma função"""
        # Procurar por Function ou Method (via Class) na árvore de contexto
        current = cursor.parent_cursor
        enclosing_function = None
        enclosing_class = None
        
        # Find the immediate enclosing function
        while current is not None:
            node = current.node
            if isinstance(node, Function):
                if enclosing_function is None:
                    enclosing_function = node
                    # Continue looking for the enclosing class
            elif isinstance(node, Class):
                enclosing_class = node
                break
            current = current.parent_cursor
        
        if enclosing_function is None:
            raise SemanticError("Can't return from top-level code.", token="return")
        
        # Check if we're in an init method (directly, not nested) and trying to return a value
        if (enclosing_class is not None and 
            enclosing_function.name == "init" and 
            self.expr is not None and 
            not (isinstance(self.expr, Literal) and self.expr.value is None)):
            # Verify this is the direct init method, not a nested function
            init_cursor = cursor.parent_cursor
            while init_cursor is not None:
                if init_cursor.node == enclosing_function:
                    # Check if this function is directly inside the class
                    parent_of_init = init_cursor.parent_cursor
                    if parent_of_init is not None and parent_of_init.node == enclosing_class:
                        raise SemanticError("Can't return a value from an initializer.", token="return")
                    break
                init_cursor = init_cursor.parent_cursor

    def eval(self, ctx: Ctx):
        value = self.expr.eval(ctx)
        raise LoxReturn(value)


@dataclass
class VarDef(Stmt):
    """
    Representa uma declaração de variável.

    Ex.: var x = 42;
    """

    name: str
    value: Expr | None

    def validate_self(self, cursor: Cursor):
        """Valida se o nome da variável não é uma palavra reservada"""
        if self.name in RESERVED_WORDS:
            raise SemanticError("nome inválido", token=self.name)

    def eval(self, ctx: Ctx):
        val = self.value.eval(ctx) if self.value is not None else None
        ctx.var_def(self.name, val)


@dataclass
class If(Stmt):
    """
    Representa uma instrução condicional.

    Ex.: if (x > 0) { ... } else { ... }
    """

    cond: Expr
    then: Stmt
    orelse: Optional[Stmt] = None

    def eval(self, ctx: Ctx):
        cond = self.cond.eval(ctx)
        if is_lox_true(cond):
            self.then.eval(ctx)
        elif self.orelse is not None:
            self.orelse.eval(ctx)




@dataclass
class While(Stmt):
    """
    Representa um laço de repetição.

    Ex.: while (x > 0) { ... }
    """

    cond: Expr
    body: Stmt

    def eval(self, ctx: Ctx):
        cond = self.cond.eval(ctx)
        if is_lox_true(cond):
            self.body.eval(ctx)
            self.eval(ctx)


@dataclass
class Block(Stmt):
    """
    Representa bloco de comandos.
    Ex.: { var x = 42; print x;  }
    """
    stmts: list[Stmt]

    def validate_self(self, cursor: Cursor):
        """Valida que não há declarações de variáveis duplicadas no mesmo bloco"""
        declared_vars = set()
        for stmt in self.stmts:
            if isinstance(stmt, VarDef):
                if stmt.name in declared_vars:
                    raise SemanticError("variável já declarada neste escopo", token=stmt.name)
                declared_vars.add(stmt.name)

    def eval(self, ctx: Ctx):
        new_ctx = ctx.push({})
        
        for stmt in self.stmts:
            stmt.eval(new_ctx)

@dataclass
class Function(Stmt):
    """
    Representa uma função.

    Ex.: fun f(x, y) { ... }
    """

    name: str
    arg_names: list[str]
    body: list[Stmt]

    def validate_self(self, cursor: Cursor):
        """Valida função: nome não reservado, parâmetros únicos e não reservados"""
        # Validar nome da função
        if self.name in RESERVED_WORDS:
            raise SemanticError("nome inválido", token=self.name)
        
        # Validar parâmetros duplicados
        if len(self.arg_names) != len(set(self.arg_names)):
            # Encontrar o primeiro duplicado
            seen = set()
            for param in self.arg_names:
                if param in seen:
                    raise SemanticError("parâmetro duplicado", token=param)
                seen.add(param)
        
        # Validar parâmetros não são palavras reservadas
        for param in self.arg_names:
            if param in RESERVED_WORDS:
                raise SemanticError("nome inválido", token=param)
        
        # Validar que variáveis no corpo não colidem com parâmetros
        param_set = set(self.arg_names)
        for stmt in self.body:
            if isinstance(stmt, VarDef) and stmt.name in param_set:
                raise SemanticError("variável colide com parâmetro", token=stmt.name)

    def eval(self, ctx: Ctx):
        func = LoxFunction(self.arg_names, self.body, ctx, self.name)
        ctx.var_def(self.name, func)
        return func


@dataclass
class Class(Stmt):
    """
    Representa uma classe.

    Ex.: class B < A { ... }
    """
    name: str
    methods: list[Function] = None
    superclass: str = None

    def validate_self(self, cursor: Cursor):
        """Valida que a classe não herda de si mesma"""
        if self.superclass is not None and self.superclass == self.name:
            raise SemanticError("A class can't inherit from itself.", token=self.name)

    def eval(self, ctx: Ctx):
        from . import runtime
        
        # Carrega a superclasse, caso exista
        superclass = None
        if self.superclass:
            superclass = ctx[self.superclass]
        
        # Avaliamos cada método
        methods = {}
        if self.methods:
            for method in self.methods:
                method_name = method.name
                method_args = method.arg_names
                method_body = method.body
                method_impl = runtime.LoxFunction(method_name, method_args, method_body, ctx)
                methods[method_name] = method_impl

        lox_class = runtime.LoxClass(self.name, methods, superclass)
        ctx.var_def(self.name, lox_class)
        return lox_class


def is_lox_true(value):
    from . import runtime
    return runtime.truthy(value)


@dataclass
class LoxFunction:
    """
    Representa uma função lox em tempo de execução
    """

    arg_names: list[str]
    body: list[Stmt]
    ctx: Ctx
    name: str = "anonymous"

    def __str__(self):
        return f"<fn {self.name}>"

    def __call__(self, *values):
        """
        self.__call__(*args) <==> self(*args)
        """
        names = self.arg_names
        if len(names) != len(values):
            msg = f"esperava {len(names)} argumentos, recebeu {len(values)}"
            raise TypeError(msg)

        # Associa cada nome em names ao valor correspondente em values
        scope = dict(zip(names, values))

        # Avalia cada comando no corpo da função dentro do escopo local
        ctx = Ctx(scope, self.ctx)
        try:
            for stmt in self.body:
                stmt.eval(ctx)
        except LoxReturn as e:
            return e.value


class LoxReturn(Exception):
    value: Value

    def __init__(self, value):
        self.value = value
        super().__init__()

def is_falsey(value):
    return value is False or value is None

@dataclass
class Expression(Stmt):
    """
    Representa uma expressão usada como statement.
    Útil para expressões de incremento em loops for.
    """
    expr: Expr

    def eval(self, ctx: Ctx):
        return self.expr.eval(ctx)

# Palavras reservadas da linguagem Lox
RESERVED_WORDS = {
    "true", "false", "nil", "and", "or", "if", "else", "for", "while", 
    "fun", "return", "class", "super", "this", "var", "print"
}

# Re-export from runtime for convenience
from .runtime import LoxClass, LoxInstance