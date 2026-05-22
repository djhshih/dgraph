# Helpers for creating condition functions

from typing import Any, Callable
from collections.abc import Iterable

Condition = Callable[["Data"], bool]


def _cond(func: Condition, *, op: str, attr: str | None = None, value: Any = None, children: list[dict] | None = None) -> Condition:
    func._dgraph_meta = {
        "op": op,
        "attr": attr,
        "value": value,
        "children": children,
    }
    return func


def _meta(func: Condition) -> dict | None:
    return getattr(func, "_dgraph_meta", None)


def equals(attr: str, value: Any) -> Condition:
    return _cond(lambda x: getattr(x, attr) == value, op="equals", attr=attr, value=value)


def contains(attr: str, value: Any) -> Condition:
    if isinstance(value, Iterable):
        return contains_any(attr, value)
    return _cond(lambda x: value in getattr(x, attr), op="contains", attr=attr, value=value)

def contains_any(attr: str, value) -> Condition:
    f = lambda x: any((v in getattr(x, attr) for v in value))
    return _cond(f, op="contains_any", attr=attr, value=value)

def contains_all(attr: str, value) -> Condition:
    f = lambda x: all((v in getattr(x, attr) for v in value))
    return _cond(f, op="contains_all", attr=attr, value=value)


def has(*values: str) -> Condition:
    return contains("attr", values)

def has_any(*values: str) -> Condition:
    return contains_any("attr", values)

def has_all(*values: str) -> Condition:
    return contains_all("attr", values)


def is_in(attr: str, value) -> Condition:
    if not (isinstance(value, tuple) or isinstance(value, list)):
        value = tuple(value)
    return _cond(lambda x: getattr(x, attr) in value, op="is_in", attr=attr, value=value)


def is_true(attr: str) -> Condition:
    return _cond(lambda x: getattr(x, attr) is True, op="is_true", attr=attr)


# NOTE  We need to be safe against None
#       Since not None == True,
#       we need to check binary variables against False and True explicitly
def is_false(attr: str) -> Condition:
    return _cond(lambda x: getattr(x, attr) is False, op="is_false", attr=attr)


def gt(attr: str, value: Any) -> Condition:
    return _cond(lambda x: getattr(x, attr) is not None and getattr(x, attr) > value, op="gt", attr=attr, value=value)


def ge(attr: str, value: Any) -> Condition:
    return _cond(lambda x: getattr(x, attr) is not None and getattr(x, attr) >= value, op="ge", attr=attr, value=value)


def lt(attr: str, value: Any) -> Condition:
    return _cond(lambda x: getattr(x, attr) is not None and getattr(x, attr) < value, op="lt", attr=attr, value=value)


def le(attr: str, value: Any) -> Condition:
    return _cond(lambda x: getattr(x, attr) is not None and getattr(x, attr) <= value, op="le", attr=attr, value=value)


def not_(f: Condition) -> Condition:
    raise "Use explicit positive predicate instead!"
    # Below implementation causes walk to advance on "cN0" at
    # not_(equals("n_status", "pN+")) instead of stopping,
    # where it will stop at equals("n_status", "pNX").
    # return lambda x: f(x) is False


def all_of(*funcs: Condition) -> Condition:
    return _cond(lambda x: all(f(x) for f in funcs), op="all_of", children=[_meta(f) for f in funcs])


def any_of(*funcs: Condition) -> Condition:
    return _cond(lambda x: any(f(x) for f in funcs), op="any_of", children=[_meta(f) for f in funcs])
