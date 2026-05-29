import dgraph.condition as dc
from dgraph.condition import Condition

from .ast import And, Expr, Group, Or, Phrase, PrefixCompare
from .parser import parse


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
        # comparison is embedded in attribute (TODO tag expansion)
        return dc.has(f"{op}{attr}")
    if op == ">":
        return dc.gt(attr, value)
    if op == ">=":
        return dc.ge(attr, value)
    if op == "<":
        return dc.lt(attr, value)
    if op == "<=":
        return dc.le(attr, value)
    raise ValueError(f"Unsupported comparison operator: {op!r}")


def _format_value(value) -> str:
    return repr(value)


def compile_expr(expr: Expr) -> str:
    if isinstance(expr, Phrase):
        return f"has({repr(expr.text)})"
    if isinstance(expr, Group):
        return compile_expr(expr.expr)
    if isinstance(expr, And):
        return f"all_of({compile_expr(expr.left)}, {compile_expr(expr.right)})"
    if isinstance(expr, Or):
        return f"any_of({compile_expr(expr.left)}, {compile_expr(expr.right)})"
    if isinstance(expr, PrefixCompare):
        attr = _phrase_text(expr.attr)
        if expr.value is None:
            return f"has({repr(f'{expr.op}{attr}')})"
        value = _coerce_value(_phrase_text(expr.value))
        helper = {">": "gt", ">=": "ge", "<": "lt", "<=": "le"}[expr.op]
        return f"{helper}({repr(attr)}, {_format_value(value)})"
    raise TypeError(f"Unsupported expr: {type(expr)!r}")


def compile_expr_from_text(text: str) -> str:
    return compile_expr(parse(text))


def condition_helpers(expr: Expr) -> tuple[str, ...]:
    used: set[str] = set()

    def visit(node: Expr) -> None:
        if isinstance(node, Phrase):
            used.add("has")
            return
        if isinstance(node, Group):
            visit(node.expr)
            return
        if isinstance(node, And):
            used.add("all_of")
            visit(node.left)
            visit(node.right)
            return
        if isinstance(node, Or):
            used.add("any_of")
            visit(node.left)
            visit(node.right)
            return
        if isinstance(node, PrefixCompare):
            if node.value is None:
                used.add("has")
            else:
                used.add({">": "gt", ">=": "ge", "<": "lt", "<=": "le"}[node.op])
            return
        raise TypeError(f"Unsupported expr: {type(node)!r}")

    visit(expr)
    return tuple(name for name in ("all_of", "any_of", "ge", "gt", "has", "le", "lt") if name in used)


def condition_helpers_from_text(text: str) -> tuple[str, ...]:
    return condition_helpers(parse(text))
