from __future__ import annotations
from dataclasses import dataclass


class Term:
    pass


@dataclass(frozen=True)
class Const(Term):
    value: int | bool

    def __str__(self) -> str:
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        return str(self.value)


@dataclass(frozen=True)
class Den(Term):
    var: str

    def __str__(self) -> str:
        return f"{self.var}=>"


@dataclass(frozen=True)
class S2(Term):
    op: str
    a: Term
    b: Term

    def __str__(self) -> str:
        return f"S2({self.op}, {self.a}, {self.b})"


@dataclass(frozen=True)
class S1(Term):
    op: str
    a: Term

    def __str__(self) -> str:
        return f"S1({self.op}, {self.a})"


@dataclass(frozen=True)
class AS(Term):
    var: str
    expr: Term

    def __str__(self) -> str:
        return f"AS_{self.var}({self.expr})"


@dataclass(frozen=True)
class Comp(Term):
    left: Term
    right: Term

    def __str__(self) -> str:
        return f"{self.left} * {self.right}"


@dataclass(frozen=True)
class IF(Term):
    cond: Term
    then: Term
    orelse: Term

    def __str__(self) -> str:
        return f"IF({self.cond}, {self.then}, {self.orelse})"


@dataclass(frozen=True)
class WH(Term):
    cond: Term
    body: Term

    def __str__(self) -> str:
        return f"WH({self.cond}, {self.body})"


@dataclass(frozen=True)
class ID(Term):
    def __str__(self) -> str:
        return "ID"
