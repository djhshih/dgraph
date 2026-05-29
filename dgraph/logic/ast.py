from dataclasses import dataclass


@dataclass(frozen=True)
class Expr:
    pass


@dataclass(frozen=True)
class Phrase(Expr):
    text: str


@dataclass(frozen=True)
class Group(Expr):
    expr: Expr


@dataclass(frozen=True)
class PrefixCompare(Expr):
    op: str
    value: Expr | None
    attr: Expr


@dataclass(frozen=True)
class And(Expr):
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Or(Expr):
    left: Expr
    right: Expr
