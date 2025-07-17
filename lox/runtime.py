import builtins
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .ctx import Ctx

if TYPE_CHECKING:
    from .ast import Stmt, Value

__all__ = [
    "add",
    "eq", 
    "ge",
    "gt",
    "le",
    "lt",
    "mul",
    "ne",
    "neg",
    "not_",
    "print",
    "show",
    "sub",
    "truthy",
    "truediv",
    "LoxFunction",
    "LoxInstance",
    "LoxClass",
    "LoxError",
    "LoxReturn",
]


class LoxClass:
    """
    Classe para representar classes Lox.
    """
    def __init__(self, name: str):
        self.name = name
    
    def __str__(self):
        return self.name
    
    def __call__(self, *args):
        # Criar uma nova instância
        instance = LoxInstance(self)
        return instance


class LoxInstance:
    """
    Classe base para todos os objetos Lox.
    """
    def __init__(self, lox_class: LoxClass):
        self.lox_class = lox_class
    
    def __str__(self):
        return f"{self.lox_class.name} instance"


@dataclass
class LoxFunction:
    """
    Classe base para todas as funções Lox.
    """

    name: str
    args: list[str]
    body: list["Stmt"]
    ctx: Ctx

    def __str__(self):
        return f"<fn {self.name}>"

    def __call__(self, *args):
        env = dict(zip(self.args, args, strict=True))
        env = self.ctx.push(env)

        try:
            for stmt in self.body:
                stmt.eval(env)
        except LoxReturn as e:
            return e.value


class LoxReturn(Exception):
    """
    Exceção para retornar de uma função Lox.
    """

    def __init__(self, value):
        self.value = value
        super().__init__()


class LoxError(Exception):
    """
    Exceção para erros de execução Lox.
    """


nan = float("nan")
inf = float("inf")


def print(value: "Value"):
    """
    Imprime um valor lox.
    """
    builtins.print(show(value))


def show(value: "Value") -> str:
    """
    Converte valor lox para string.
    """
    from .ast import LoxFunction as ASTLoxFunction
    
    if value is None:
        return "nil"
    elif value is True:
        return "true"
    elif value is False:
        return "false"
    elif isinstance(value, float):
        # Remove .0 se for um número inteiro
        if value.is_integer():
            return str(int(value))
        return str(value)
    elif isinstance(value, LoxClass):
        return str(value)
    elif isinstance(value, LoxInstance):
        return str(value)
    elif isinstance(value, (LoxFunction, ASTLoxFunction)):
        return str(value)
    elif isinstance(value, (types.FunctionType, types.BuiltinFunctionType)):
        return "<native fn>"
    else:
        return str(value)


def show_repr(value: "Value") -> str:
    """
    Mostra um valor lox, mas coloca aspas em strings.
    """
    if isinstance(value, str):
        return f'"{value}"'
    return show(value)


def truthy(value: "Value") -> bool:
    """
    Converte valor lox para booleano segundo a semântica do lox.
    """
    if value is None or value is False:
        return False
    return True


# Operações matemáticas para Lox
def add(left: "Value", right: "Value") -> "Value":
    """Soma em Lox - aceita números ou strings"""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left + right
    elif isinstance(left, str) and isinstance(right, str):
        return left + right
    else:
        raise LoxError("Operandos devem ser dois números ou duas strings.")


def sub(left: "Value", right: "Value") -> "Value":
    """Subtração em Lox - aceita apenas números"""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left - right
    else:
        raise LoxError("Operandos devem ser números.")


def mul(left: "Value", right: "Value") -> "Value":
    """Multiplicação em Lox - aceita apenas números"""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left * right
    else:
        raise LoxError("Operandos devem ser números.")


def truediv(left: "Value", right: "Value") -> "Value":
    """Divisão em Lox - aceita apenas números"""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if right == 0:
            raise LoxError("Divisão por zero.")
        return left / right
    else:
        raise LoxError("Operandos devem ser números.")


def neg(value: "Value") -> "Value":
    """Negação em Lox - aceita apenas números"""
    if isinstance(value, (int, float)):
        return -value
    else:
        raise LoxError("Operando deve ser um número.")


# Operações de comparação para Lox
def gt(left: "Value", right: "Value") -> bool:
    """Maior que em Lox - aceita apenas números"""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left > right
    else:
        raise LoxError("Operandos devem ser números.")


def ge(left: "Value", right: "Value") -> bool:
    """Maior ou igual em Lox - aceita apenas números"""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left >= right
    else:
        raise LoxError("Operandos devem ser números.")


def lt(left: "Value", right: "Value") -> bool:
    """Menor que em Lox - aceita apenas números"""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left < right
    else:
        raise LoxError("Operandos devem ser números.")


def le(left: "Value", right: "Value") -> bool:
    """Menor ou igual em Lox - aceita apenas números"""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left <= right
    else:
        raise LoxError("Operandos devem ser números.")


def eq(left: "Value", right: "Value") -> bool:
    """Igualdade estrita em Lox - não aceita conversões de tipo"""
    # Em Lox, valores de tipos diferentes são sempre diferentes
    if type(left) != type(right):
        return False
    return left == right


def ne(left: "Value", right: "Value") -> bool:
    """Desigualdade estrita em Lox"""
    return not eq(left, right)


def not_(value: "Value") -> bool:
    """Negação lógica em Lox"""
    return not truthy(value)
