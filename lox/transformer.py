"""
Implementa o transformador da árvore sintática que converte entre as representações

    lark.Tree -> lox.ast.Node.

A resolução de vários exercícios requer a modificação ou implementação de vários
métodos desta classe.
"""

from typing import Callable
from lark import Transformer, v_args, Token

from . import runtime as op
from .ast import *


def op_handler(op: Callable):
    """
    Fábrica de métodos que lidam com operações binárias na árvore sintática.

    Recebe a função que implementa a operação em tempo de execução.
    """

    def method(self, left, right):
        return BinOp(left, right, op)

    return method


@v_args(inline=True)
class LoxTransformer(Transformer):
    # Programa
    def program(self, *stmts):
        return Program(list(stmts))

    # Operações matemáticas básicas
    mul = op_handler(op.mul)
    div = op_handler(op.truediv)
    sub = op_handler(op.sub)
    add = op_handler(op.add)

    # Comparações
    gt = op_handler(op.gt)
    lt = op_handler(op.lt)
    ge = op_handler(op.ge)
    le = op_handler(op.le)
    eq = op_handler(op.eq)
    ne = op_handler(op.ne)

    # Outras expressões
    def call(self, callee,*args):
        if len(args) == 1 and isinstance(args[0], list):
            params = args[0]
        else:
            params = list(args)
        return Call(callee, params)

    def params(self, *args):
        params = list(args)
        return params

    # Comandos
    def __init__(self):
        super().__init__()
        self._in_block = False  # Track if we're currently transforming inside a block
        
    def block(self, *stmts: Stmt):
        # Set flag to indicate we're processing a block
        old_in_block = self._in_block
        self._in_block = True
        
        # Process each statement in the block
        processed_stmts = []
        for stmt in stmts:
            if isinstance(stmt, VarDef) and stmt.value is not None:
                # Check for self-reference in local variable initializers
                self._check_self_reference_in_initializer(stmt.name, stmt.value)
            processed_stmts.append(stmt)
        
        # Restore previous state
        self._in_block = old_in_block
        return Block(processed_stmts)

    def assign(self, var, value: Expr):
        var_name = var.name if hasattr(var, 'name') else str(var)
        return Assign(var_name, value)

    def getattr(self, obj, attr):
        if isinstance(attr, Token):
            attr_name = attr.value
        elif hasattr(attr, 'name'):
            attr_name = attr.name
        else:
            attr_name = str(attr)
        
        return Getattr(obj, attr_name, None)
    
    def super_getattr(self, super_token, attr):
        if isinstance(attr, Token):
            attr_name = attr.value
        elif hasattr(attr, 'name'):
            attr_name = attr.name
        else:
            attr_name = str(attr)
        return Getattr(Super(), attr_name, None)

    def setattr(self, obj, attr, value):
        if isinstance(attr, Token):
            attr_name = attr.value
        elif hasattr(attr, 'name'):
            attr_name = attr.name
        else:
            attr_name = str(attr)
        return Setattr(obj, attr_name, value)

    def and_(self, left, right):
        return And(left, right)

    def or_(self, left, right):
        return Or(left, right)

    def neg(self, expr):
        return UnaryOp(expr=expr, op=op.neg)

    def not_(self, expr):
        return UnaryOp(expr=expr, op=op.not_)


    def print_cmd(self, token, expr: Expr) -> Print:
        return Print(expr)

    def var_def(self, token, var: Var, value: Expr|None = None):
        return VarDef(var.name, value)
    
    def _check_self_reference_in_initializer(self, var_name: str, expr: Expr):
        """Check if the expression references the variable being declared"""
        from .ast import Var as VarExpr, BinOp, UnaryOp, Call, Getattr, Setattr
        
        if isinstance(expr, VarExpr):
            if expr.name == var_name:
                from .errors import SemanticError
                raise SemanticError(f"Can't read local variable in its own initializer.", token=var_name)
        elif isinstance(expr, BinOp):
            self._check_self_reference_in_initializer(var_name, expr.left)
            self._check_self_reference_in_initializer(var_name, expr.right)
        elif isinstance(expr, UnaryOp):
            self._check_self_reference_in_initializer(var_name, expr.expr)
        elif isinstance(expr, Call):
            self._check_self_reference_in_initializer(var_name, expr.callee)
            if expr.params:
                for arg in expr.params:
                    if arg is not None:
                        self._check_self_reference_in_initializer(var_name, arg)
        elif isinstance(expr, Getattr):
            self._check_self_reference_in_initializer(var_name, expr.attr_main)
            if isinstance(expr.subattr, Expr):
                self._check_self_reference_in_initializer(var_name, expr.subattr)
        elif isinstance(expr, Setattr):
            self._check_self_reference_in_initializer(var_name, expr.target)
            self._check_self_reference_in_initializer(var_name, expr.value)

    def if_cmd(self, *args):
        # Args can be: [IF_token, cond, then] or [IF_token, cond, then, ELSE_token, orelse]
        if len(args) == 3:
            token, cond, then = args
            return If(cond, then, None)
        elif len(args) == 5:
            token, cond, then, else_token, orelse = args
            return If(cond, then, orelse)
        else:
            raise ValueError(f"if_cmd expected 3 or 5 args, got {len(args)}: {args}")

    def while_cmd(self, token, cond: Expr, body: Stmt):
        return While(cond, body)

    def for_init(self, *args):
        if len(args) == 0:
            return Literal(None)
        return args[0]

    def for_cond(self, *args):
        if len(args) == 0:
            return Literal(True)
        return args[0]

    def for_incr(self, *args):
        if len(args) == 0:
            return Literal(None)
        return args[0]

    def for_cmd(self, token, init, cond, incr, body):
        """
        Transforma for (init; cond; incr) body em:
        {
            init;
            while (cond) {
                body;
                incr;
            }
        }
        """
        statements = []
        
        if init is not None and not (isinstance(init, Literal) and init.value is None):
            statements.append(init)

        while_body = body
        
        if incr is not None and not (isinstance(incr, Literal) and incr.value is None):
            if isinstance(body, Block):
                while_body = Block(body.stmts + [Expression(incr)])
            else:
                while_body = Block([body, Expression(incr)])
        
        while_loop = While(cond, while_body)
        statements.append(while_loop)
        
        return Block(statements)

    def fun_def(self, token, name: Var, args: list[str], body: Block):
        return Function(name.name, args, body.stmts)
        
    def fun_args(self, *args: Var) -> list[str]:
        return [arg.name for arg in args if arg is not None]
    
    def return_cmd(self, token, expr: Expr = None):
        if expr is None:
            expr = Literal(None)
        return Return(expr)

    def VAR(self, token) -> Var:
        name = str(token)
        return Var(name)

    def NUMBER(self, token) -> Literal:
        num = float(token)
        return Literal(num)

    def STRING(self, token) -> Literal:
        text = str(token)[1:-1]
        return Literal(text)

    def NIL(self, _) -> Literal:
        return Literal(None)

    def BOOL(self, token) -> Literal:
        return Literal(token == "true")

    def empty(self, _=None):
        return Literal(None)

    def true_expr(self, _=None):
        return Literal(True)

    def class_def(self, token, name, *args):
        """Transforma definição de classe"""
        name_str = name.name if hasattr(name, 'name') else str(name)
        
        # Analisar argumentos: pode ser [superclass, methods] ou apenas [methods]
        superclass_str = None
        methods = []
        
        if len(args) == 1:
            # Apenas methods
            methods = args[0] if args[0] else []
        elif len(args) == 2:
            # superclass e methods
            superclass = args[0]
            methods = args[1] if args[1] else []
            superclass_str = superclass.name if superclass and hasattr(superclass, 'name') else None
            
        return Class(name_str, methods, superclass_str)

    def class_body(self, *methods):
        """Transforma corpo da classe"""
        return list(methods)

    def method_def(self, name: Var, args: list[str], body: Block):
        """Transforma definição de método"""
        return Function(name.name, args, body.stmts)

    def this_expr(self, token):
        return This()