from dataclasses import dataclass

import dgraph.condition as dc
from dgraph.condition import Condition

from .ast import And, Expr, Group, Or, Phrase, PrefixCompare
from .parser import parse


@dataclass(frozen=True)
class Interpretation:
    expr: Expr
    condition: Condition


def _compile(expr: Expr) -> Condition:
    if isinstance(expr, Phrase):
        return dc.has(expr.text)
    if isinstance(expr, Group):
        return _compile(expr.expr)
    if isinstance(expr, And):
        return dc.all_of(_compile(expr.left), _compile(expr.right))
    if isinstance(expr, Or):
        return dc.any_of(_compile(expr.left), _compile(expr.right))
    if isinstance(expr, PrefixCompare):
        attr = _phrase_text(expr.attr)
        value = None if expr.value is None else _coerce_value(_phrase_text(expr.value))
        return _comparison_condition(expr.op, attr, value)
    raise TypeError(f"Unsupported expr: {type(expr)!r}")


def _phrase_text(expr: Expr) -> str:
    if not isinstance(expr, Phrase):
        raise TypeError(f"Expected Phrase, got {type(expr)!r}")
    return expr.text


def _coerce_value(text: str):
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def _comparison_condition(op: str, attr: str, value) -> Condition:
    if value is None:
        # comparison is embedded in attribute
        return dc.has(attr)
    if op == ">":
        return dc.gt(attr, value)
    if op == ">=":
        return dc.ge(attr, value)
    if op == "<":
        return dc.lt(attr, value)
    if op == "<=":
        return dc.le(attr, value)
    raise ValueError(f"Unsupported comparison operator: {op!r}")


def interpret(text: str) -> Interpretation:
    expr = parse(text)
    condition = _compile(expr)
    return Interpretation(expr=expr, condition=condition)


def infer_condition(text: str) -> Condition:
    return interpret(text).condition
