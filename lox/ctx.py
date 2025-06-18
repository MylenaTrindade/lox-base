import math
import time
from dataclasses import field
from typing import TYPE_CHECKING, Iterator, Optional, TypeVar

from lox.ast import dataclass

if TYPE_CHECKING:
    from .ast import Value

T = TypeVar("T")
ScopeDict = dict[str, "Value"]


class _Builtins(dict):
    BUILTINS: dict[str, "Value"] = {
        "sqrt": math.sqrt,
        "clock": time.time,
        "max": max,
    }

    def __init__(self):
        super().__init__(self.BUILTINS)

    def __repr__(self) -> str:
        return "BUILTINS"

    def __str__(self) -> str:
        return self.__repr__()


BUILTINS = _Builtins()


@dataclass
class Ctx:
    """
    Contexto de execução. Por enquanto é só um dicionário que armazena nomes
    das variáveis e seus respectivos valores.
    """

    scope: ScopeDict = field(default_factory=dict)
    parent: Optional["Ctx"] = field(default_factory=lambda: Ctx(BUILTINS, None))

    @classmethod
    def from_dict(cls, env: ScopeDict) -> "Ctx":
        """
        Cria um novo contexto a partir de um dicionário.
        """
        return cls(env, Ctx(BUILTINS, None))

    def __getitem__(self, key):
        """Busca uma variável no escopo atual ou nos escopos pais"""
        try:
            return self.scope[key]
        except KeyError:
            if self.parent is not None:
                return self.parent[key]
            raise KeyError(f"Variável '{key}' não encontrada")

    def __setitem__(self, key, value):
        """
        Define o valor de uma variável existente no escopo atual ou em um escopo pai.
        Se a variável não existir em nenhum escopo, lança KeyError.
        """
        if key in self.scope:
            self.scope[key] = value
        elif self.parent is not None:
            self.parent[key] = value
        else:
            raise KeyError(f"Variável '{key}' não foi declarada")

    def __contains__(self, name: str) -> bool:
        """
        Verifica se uma variável existe no contexto.
        """
        return name in self.scope or (self.parent is not None and name in self.parent)

    def var_def(self, key, value=None):
        """
        Define uma nova variável no escopo atual.
        Se a variável já existir no escopo atual (não nos escopos pais) e
        não estivermos no escopo global, lança um erro.
        """
        if key in self.scope and not self.is_global():
            raise NameError(f"Variável '{key}' já foi declarada neste escopo")
        self.scope[key] = value

    def to_dict(self) -> ScopeDict:
        """
        Converte o contexto para um dicionário.
        """
        if self.parent is None:
            return self.scope.copy()
        return {**self.parent.to_dict(), **self.scope}

    def iter_scopes(self, reverse: bool = False) -> Iterator[ScopeDict]:
        """
        Itera sobre os ambientes do contexto, começando pelo mais interno.
        """
        if reverse:
            if self.parent is not None:
                yield from self.parent.iter_scopes(reverse=True)
            yield self.scope
        else:
            yield self.scope
            if self.parent is not None:
                yield from self.parent.iter_scopes()

    def pretty(self) -> str:
        """
        Representação do contexto como string.
        """

        lines: list[str] = []
        for i, scope in enumerate(self.iter_scopes(reverse=True)):
            lines.append(pretty_scope(scope, i))
        return "\n".join(reversed(lines))

    def pop(self):
        """Remove o escopo mais interno e retorna (escopo, contexto_pai)"""
        if self.parent is None:
            raise RuntimeError("Cannot pop the global scope.")
        return self.scope, self.parent

    def push(self, scope=None):
        """Cria um novo contexto com um novo escopo, tendo o contexto atual como pai"""
        return Ctx(scope or {}, self)

    def is_global(self) -> bool:
        """
        Verifica se o contexto atual é o escopo global.
        """
        if self.parent is None:
            return False
        return self.parent.parent is None


def pretty_scope(env: ScopeDict, index: int) -> str:
    """
    Representa um escopo como string.
    """
    if not env:
        return f"{index:>2}: <empty>"
    items = (f"{k} = {v}" for k, v in sorted(env.items()))
    data = "; ".join(items)
    return f"{index:>2}: {data}"