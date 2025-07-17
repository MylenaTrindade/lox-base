import builtins
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

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


@dataclass
class LoxClass:
    """
    Classe para representar classes Lox.
    """
    name: str
    methods: dict[str, "LoxFunction"] = None
    base: Optional["LoxClass"] = None
    
    def __post_init__(self):
        if self.methods is None:
            self.methods = {}
    
    def __str__(self):
        return self.name
    
    def __call__(self, *args):
        # Criar uma nova instância
        instance = LoxInstance(self)
        
        # Se a classe tem um método init, chama-lo automaticamente
        try:
            init_method = self.get_method("init")
            bound_init = init_method.bind(instance)
            bound_init(*args)
        except LoxError:
            # Se não há método init, mas foram passados argumentos, é um erro
            if args:
                raise LoxError(f"Expected 0 arguments but got {len(args)}.")
        
        return instance
    
    def get_method(self, name: str) -> "LoxFunction":
        """
        Busca um método na classe atual ou nas bases.
        """
        return self.get_method_with_class(name)[0]
    
    def get_method_with_class(self, name: str) -> tuple["LoxFunction", "LoxClass"]:
        """
        Busca um método na classe atual ou nas bases, retornando o método e a classe onde foi definido.
        """
        if name in self.methods:
            return self.methods[name], self
        
        if self.base is not None:
            return self.base.get_method_with_class(name)
        
        raise LoxError(f"Undefined property '{name}'.")


class LoxInstance:
    """
    Classe base para todos os objetos Lox.
    """
    def __init__(self, lox_class: LoxClass):
        self.__lox_class = lox_class
        self.fields = {}
    
    def __str__(self):
        return f"{self.__lox_class.name} instance"
    
    def __getattr__(self, name: str):
        """
        Acesso a atributos que não existem - busca métodos na classe.
        """
        # Primeiro verifica se é um campo
        if name in self.fields:
            return self.fields[name]
        
        # Buscar método na classe
        try:
            method, defining_class = self.__lox_class.get_method_with_class(name)
            # Bind the method to this instance
            return method.bind_with_class(self, defining_class)
        except LoxError:
            raise AttributeError(f"'{self.__lox_class.name}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value):
        """
        Define atributos - usa fields para atributos Lox.
        """
        if name.startswith('_LoxInstance__') or name == 'fields':
            # Atributos privados e fields vão para __dict__
            super().__setattr__(name, value)
        else:
            # Atributos Lox vão para fields
            if not hasattr(self, 'fields'):
                super().__setattr__('fields', {})
            self.fields[name] = value
    
    def get(self, name: str):
        """
        Obtém um campo ou método da instância.
        """
        if name in self.fields:
            return self.fields[name]
        
        # Buscar método na classe
        try:
            method, defining_class = self.__lox_class.get_method_with_class(name)
            # Special case: init method should return a bound function that returns the instance
            if name == "init":
                return InitBoundMethod(self, method)
            else:
                # Bind the method to this instance
                return method.bind_with_class(self, defining_class)
        except LoxError:
            raise LoxError(f"Undefined property '{name}'.")
    
    def set(self, name: str, value):
        """
        Define um campo da instância.
        """
        self.fields[name] = value
    

class BoundMethod:
    """
    Representa um método vinculado a uma instância.
    """
    def __init__(self, instance: LoxInstance, method: "LoxFunction"):
        self.instance = instance
        self.method = method
    
    def __call__(self, *args):
        # Criar um novo contexto que inclui 'this' e possivelmente 'super'
        context_vars = {'this': self.instance}
        
        # Se a classe tem uma superclasse, injeta 'super'
        instance_class = getattr(self.instance, '_LoxInstance__lox_class')
        if instance_class.base is not None:
            # super é uma instância especial que delega para a superclasse
            super_instance = SuperInstance(self.instance, instance_class.base)
            context_vars['super'] = super_instance
            
        new_ctx = self.method.closure.push(context_vars)
        return self.method.call(*args, ctx=new_ctx)


@dataclass
class LoxFunction:
    """
    Classe base para todas as funções Lox.
    """

    name: str
    args: list[str]
    body: list["Stmt"]
    ctx: Ctx
    _identity: object = None

    def __post_init__(self):
        if self._identity is None:
            self._identity = object()

    @property
    def closure(self):
        return self.ctx

    def __str__(self):
        return f"<fn {self.name}>"

    def __call__(self, *args):
        from .ast import LoxReturn
        env = dict(zip(self.args, args, strict=True))
        env = self.ctx.push(env)

        try:
            for stmt in self.body:
                stmt.eval(env)
        except LoxReturn as e:
            return e.value
    
    def call(self, *args, ctx=None):
        """
        Chama a função com um contexto específico.
        """
        from .ast import LoxReturn
        if ctx is None:
            ctx = self.ctx
        
        env = dict(zip(self.args, args, strict=True))
        env = ctx.push(env)

        try:
            for stmt in self.body:
                stmt.eval(env)
        except LoxReturn as e:
            return e.value

    def bind(self, obj) -> "LoxFunction":
        """
        Cria uma nova LoxFunction com 'this' ligado ao objeto especificado.
        """
        # For backward compatibility, use the object's class for super resolution
        if hasattr(obj, '_LoxInstance__lox_class'):
            defining_class = getattr(obj, '_LoxInstance__lox_class')
        else:
            defining_class = None
        return self.bind_with_class(obj, defining_class)
    
    def bind_with_class(self, obj, defining_class: "LoxClass") -> "LoxFunction":
        """
        Cria uma nova LoxFunction com 'this' ligado ao objeto especificado e super baseado na classe definidora.
        """
        context_vars = {"this": obj}
        
        # Se a classe definidora tem uma superclasse, injeta 'super'
        if defining_class is not None and defining_class.base is not None:
            super_instance = SuperInstance(obj, defining_class.base)
            context_vars['super'] = super_instance
        
        bound_ctx = self.ctx.push(context_vars)
        return LoxFunction(
            name=self.name,
            args=self.args,
            body=self.body,
            ctx=bound_ctx,
            _identity=object()  # Each bound method gets unique identity
        )


class LoxError(Exception):
    """
    Exceção para erros de execução Lox.
    """


@dataclass 
class SuperInstance:
    """
    Instância especial que delega métodos para a superclasse.
    Usada para implementar a funcionalidade 'super' em Lox.
    """
    instance: "LoxInstance"
    superclass: "LoxClass"
    
    def get(self, name: str):
        """
        Obtém um método da superclasse e o vincula à instância original.
        """
        method = self.superclass.get_method(name)
        return method.bind(self.instance)

    def __getattr__(self, name: str):
        """Para compatibilidade com acesso de atributos Python"""
        return self.get(name)


@dataclass
class InitBoundMethod:
    """
    Representa um método init vinculado a uma instância.
    Diferente de BoundMethod, sempre retorna a instância.
    """
    instance: "LoxInstance"
    method: "LoxFunction"
    
    def __call__(self, *args):
        # Execute o método init normalmente
        bound_method = self.method.bind(self.instance)
        bound_method(*args)
        # Mas sempre retorne a instância, não o resultado
        return self.instance


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
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be two numbers or two strings.")
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left + right
    elif isinstance(left, str) and isinstance(right, str):
        return left + right
    else:
        raise LoxError("Operands must be two numbers or two strings.")


def sub(left: "Value", right: "Value") -> "Value":
    """Subtração em Lox - aceita apenas números"""
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left - right
    else:
        raise LoxError("Operands must be numbers.")


def mul(left: "Value", right: "Value") -> "Value":
    """Multiplicação em Lox - aceita apenas números"""
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left * right
    else:
        raise LoxError("Operands must be numbers.")


def truediv(left: "Value", right: "Value") -> "Value":
    """Divisão em Lox - aceita apenas números"""
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if right == 0:
            raise LoxError("Divisão por zero.")
        return left / right
    else:
        raise LoxError("Operands must be numbers.")


def neg(value: "Value") -> "Value":
    """Negação em Lox - aceita apenas números"""
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(value, bool):
        raise LoxError("Operand must be a number.")
    elif isinstance(value, (int, float)):
        return -value
    else:
        raise LoxError("Operand must be a number.")


# Operações de comparação para Lox
def gt(left: "Value", right: "Value") -> bool:
    """Maior que em Lox - aceita apenas números"""
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left > right
    else:
        raise LoxError("Operands must be numbers.")


def ge(left: "Value", right: "Value") -> bool:
    """Maior ou igual em Lox - aceita apenas números"""
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left >= right
    else:
        raise LoxError("Operands must be numbers.")


def lt(left: "Value", right: "Value") -> bool:
    """Menor que em Lox - aceita apenas números"""
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left < right
    else:
        raise LoxError("Operands must be numbers.")


def le(left: "Value", right: "Value") -> bool:
    """Menor ou igual em Lox - aceita apenas números"""
    # Check for booleans first since bool is a subclass of int in Python
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left <= right
    else:
        raise LoxError("Operands must be numbers.")


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
