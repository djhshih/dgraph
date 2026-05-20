# Helpers for creating condition functions

from typing import Any, Callable

Condition = Callable[["Data"], bool]


def cond(func: Condition, *, op: str, attr: str | None = None, value: Any = None, values: tuple[Any, ...] | None = None, children: list[dict] | None = None) -> Condition:
    func._dgraph_meta = {
        "op": op,
        "attr": attr,
        "value": value,
        "values": values,
        "children": children,
    }
    return func


def _meta_of(func: Condition) -> dict | None:
    return getattr(func, "_dgraph_meta", None)


def always() -> Condition:
    return cond(lambda x: True, op="always")


def equals(attr: str, value: Any) -> Condition:
    return cond(lambda x: getattr(x, attr) == value, op="equals", attr=attr, value=value)


def is_in(attr: str, values) -> Condition:
    values = tuple(values)
    return cond(lambda x: getattr(x, attr) in values, op="is_in", attr=attr, values=values)


def is_true(attr: str) -> Condition:
    return cond(lambda x: getattr(x, attr) is True, op="is_true", attr=attr)


# NOTE  We need to be safe against None
#       Since not None == True,
#       we need to check binary variables against False and True explicitly
def is_false(attr: str) -> Condition:
    return cond(lambda x: getattr(x, attr) is False, op="is_false", attr=attr)


def gt(attr: str, value: Any) -> Condition:
    return cond(lambda x: getattr(x, attr) is not None and getattr(x, attr) > value, op="gt", attr=attr, value=value)


def ge(attr: str, value: Any) -> Condition:
    return cond(lambda x: getattr(x, attr) is not None and getattr(x, attr) >= value, op="ge", attr=attr, value=value)


def lt(attr: str, value: Any) -> Condition:
    return cond(lambda x: getattr(x, attr) is not None and getattr(x, attr) < value, op="lt", attr=attr, value=value)


def le(attr: str, value: Any) -> Condition:
    return cond(lambda x: getattr(x, attr) is not None and getattr(x, attr) <= value, op="le", attr=attr, value=value)


def not_(f: Condition) -> Condition:
    raise "Use explicit positive predicate instead!"
    # Below implementation causes walk to advance on "cN0" at
    # not_(equals("n_status", "pN+")) instead of stopping,
    # where it will stop at equals("n_status", "pNX").
    # return lambda x: f(x) is False


def all_of(*funcs: Condition) -> Condition:
    return cond(lambda x: all(f(x) for f in funcs), op="all_of", children=[_meta_of(f) for f in funcs])


def any_of(*funcs: Condition) -> Condition:
    return cond(lambda x: any(f(x) for f in funcs), op="any_of", children=[_meta_of(f) for f in funcs])
