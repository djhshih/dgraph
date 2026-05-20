# Helpers for creating condition functions

from typing import Any, Callable

Condition = Callable[["Data"], bool]


def equals(attr: str, value: Any) -> Condition:
    return lambda x: getattr(x, attr) == value


def contains(attr: str, values) -> Condition:
    return lambda x: getattr(x, attr) in values


def is_true(attr: str) -> Condition:
    return lambda x: getattr(x, attr) is True


# NOTE  We need to be safe against None
#       Since not None == True,
#       we need to check binary variables against False and True explicitly
def is_false(attr: str) -> Condition:
    return lambda x: getattr(x, attr) is False


def gt(attr: str, value: Any) -> Condition:
    return lambda x: getattr(x, attr) is not None and getattr(x, attr) > value


def ge(attr: str, value: Any) -> Condition:
    return lambda x: getattr(x, attr) is not None and getattr(x, attr) >= value


def lt(attr: str, value: Any) -> Condition:
    return lambda x: getattr(x, attr) is not None and getattr(x, attr) < value


def le(attr: str, value: Any) -> Condition:
    return lambda x: getattr(x, attr) is not None and getattr(x, attr) <= value


def not_(f: Condition) -> Condition:
    raise "Use explicit positive predicate instead!"
    # Below implementation causes walk to advance on "cN0" at
    # not_(equals("n_status", "pN+")) instead of stopping,
    # where it will stop at equals("n_status", "pNX").
    # return lambda x: f(x) is False


def all_of(*funcs: Condition) -> Condition:
    return lambda x: all(f(x) for f in funcs)


def any_of(*funcs: Condition) -> Condition:
    return lambda x: any(f(x) for f in funcs)


