from __future__ import annotations
from dataclasses import dataclass
from .span import SourceSpan


@dataclass(frozen=True, kw_only=True)
class ASTNode:
    span: SourceSpan | None = None


@dataclass(frozen=True)
class Program(ASTNode):
    body: ASTNode


@dataclass(frozen=True)
class Seq(ASTNode):
    first: ASTNode
    second: ASTNode


@dataclass(frozen=True)
class Assign(ASTNode):
    var: str
    expr: ASTNode


@dataclass(frozen=True)
class Skip(ASTNode):
    pass


@dataclass(frozen=True)
class If(ASTNode):
    cond: ASTNode
    then: ASTNode
    orelse: ASTNode


@dataclass(frozen=True)
class While(ASTNode):
    cond: ASTNode
    body: ASTNode


@dataclass(frozen=True)
class Block(ASTNode):
    body: ASTNode


@dataclass(frozen=True)
class Num(ASTNode):
    value: int


@dataclass(frozen=True)
class Var(ASTNode):
    name: str


@dataclass(frozen=True)
class BinOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode


@dataclass(frozen=True)
class BoolConst(ASTNode):
    value: bool


@dataclass(frozen=True)
class Rel(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode


@dataclass(frozen=True)
class Not(ASTNode):
    operand: ASTNode


@dataclass(frozen=True)
class Logic(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
