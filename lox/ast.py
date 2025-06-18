from abc import ABC
from dataclasses import dataclass
from typing import Callable, Union

from .ctx import Ctx

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
    
        args = [param.eval(ctx) for param in self.params]
        
        return func(*args)

    def _eval_callee(self, ctx):
        callee = self.callee
        if isinstance(callee, Var):
            val = ctx[callee.name]
            # print(f"Resolvido Var: {callee.name} -> {val} ({type(val)})")  # COMENTE OU REMOVA
            return val
        elif isinstance(callee, Getattr):
            obj = callee.attr_main.eval(ctx)
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


@dataclass
class Super(Expr):
    """
    Acesso a method ou atributo da superclasse.

    Ex.: super.x
    """


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

        # Primeiro nível: getattr(obj, attr)
        value = getattr(obj, self.attr)

        # Encadeamento: getattr(obj.attr, subattr)
        if self.subattr is not None:
            if isinstance(self.subattr, Var):
                subattr_name = self.subattr.name
            elif isinstance(self.subattr, Expr):
                subattr_name = self.subattr.eval(ctx)
            else:
                subattr_name = self.subattr

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
        value = self.expr.eval(ctx)
        print(value)


@dataclass
class Return(Stmt):
    """
    Representa uma instrução de retorno.

    Ex.: return x;
    """

    expr: Expr

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
    orelse: Stmt

    def eval(self, ctx: Ctx):
        cond = self.cond.eval(ctx)
        if is_lox_true(cond):
            self.then.eval(ctx)
        else:
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

    def eval(self, ctx: Ctx):
        func = LoxFunction(self.arg_names, self.body, ctx)
        ctx.var_def(self.name, func)
        return func


@dataclass
class Class(Stmt):
    """
    Representa uma classe.

    Ex.: class B < A { ... }
    """


def is_lox_true(value):
    return (value is not False) and (value is not None)


@dataclass
class LoxFunction:
    """
    Representa uma função lox em tempo de execução
    """

    arg_names: list[str]
    body: list[Stmt]
    ctx: Ctx

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