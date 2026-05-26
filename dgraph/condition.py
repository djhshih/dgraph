# Helpers for creating condition functions

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Condition:
    predicate: Callable[["Data"], bool]
    attrs: tuple[str, ...] = ()

    def __call__(self, data: "Data") -> bool:
        return self.predicate(data)


def _is_multi(x: Any) -> bool:
    return isinstance(x, (list, tuple, set))


def _numeric_compare(attr: str, value: Any, op: Callable[[Any, Any], bool]) -> Condition:
    return _cond(lambda x: getattr(x, attr) is not None and op(getattr(x, attr), value), attr)


def _cond(func: Callable[["Data"], bool], *attrs: str) -> Condition:
    return Condition(func, attrs=tuple(dict.fromkeys(attr for attr in attrs if attr)))


def equals(attr: str, value: Any) -> Condition:
    return _cond(lambda x: getattr(x, attr) == value, attr)


def contains(attr: str, value: Any) -> Condition:
    if _is_multi(value):
        raise TypeError("value must be scalar type, but got: {}".format(value))
    return _cond(lambda x: value in getattr(x, attr), value if attr == "tags" else attr)

def contains_any(attr: str, value: Any) -> Condition:
    values = tuple(value) if isinstance(value, set) else value
    return _cond(lambda x: any(v in getattr(x, attr) for v in values), value if attr == "tags" else attr)


def contains_all(attr: str, value: Any) -> Condition:
    values = tuple(value) if isinstance(value, set) else value
    return _cond(lambda x: all(v in getattr(x, attr) for v in values), value if attr == "tags" else attr)


def has(value: str) -> Condition:
    return contains("tags", value)

def has_any(*values: str) -> Condition:
    return contains_any("tags", values)

def has_all(*values: str) -> Condition:
    return contains_all("tags", values)


def is_in(attr: str, value: Any) -> Condition:
    if _is_multi(getattr(x, attr)):
        raise TypeError("attr {} must refer to a scalar type".format(attr))
    normalized = value if isinstance(value, (tuple, list)) else tuple(value)
    return _cond(lambda x: getattr(x, attr) in normalized, attr)


def is_true(attr: str) -> Condition:
    return _cond(lambda x: getattr(x, attr) is True, attr)


# NOTE  We need to be safe against None
#       Since not None == True,
#       we need to check binary variables against False and True explicitly
def is_false(attr: str) -> Condition:
    return _cond(lambda x: getattr(x, attr) is False, attr)


def gt(attr: str, value: Any) -> Condition:
    return _numeric_compare(attr, value, lambda a, b: a > b)


def ge(attr: str, value: Any) -> Condition:
    return _numeric_compare(attr, value, lambda a, b: a >= b)


def lt(attr: str, value: Any) -> Condition:
    return _numeric_compare(attr, value, lambda a, b: a < b)


def le(attr: str, value: Any) -> Condition:
    return _numeric_compare(attr, value, lambda a, b: a <= b)


def not_(f: Condition) -> Condition:
    raise RuntimeError("Use explicit positive predicate instead!")
    # Below implementation causes walk to advance on "cN0" at
    # not_(equals("n_status", "pN+")) instead of stopping,
    # where it will stop at equals("n_status", "pNX").
    # return lambda x: f(x) is False


def all_of(*funcs: Condition) -> Condition:
    attrs = tuple(attr for func in funcs for attr in getattr(func, "attrs", ()))
    return _cond(lambda x: all(f(x) for f in funcs), *attrs)


def any_of(*funcs: Condition) -> Condition:
    attrs = tuple(attr for func in funcs for attr in getattr(func, "attrs", ()))
    return _cond(lambda x: any(f(x) for f in funcs), *attrs)
