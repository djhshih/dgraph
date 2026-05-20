from dataclasses import dataclass, field
from typing import Any, Callable

import dgraph.condition as dc


@dataclass
class Data:
    pass


@dataclass
class Node:
    label: str
    condition: Callable[["Data"], bool] = lambda x: True
    children: list["Node"] = field(default_factory=list)


def branch(label: str, condition: Callable[["Data"], bool], *children: "Node") -> Node:
    return Node(label, condition=condition, children=list(children))


def _coerce_node(item: str | Node) -> Node:
    if isinstance(item, Node):
        return item
    return Node(str(item))


def chain(*items: str | Node) -> Node:
    if not items:
        raise ValueError("chain() requires at least one label or node")

    nodes = [_coerce_node(item) for item in items]
    current = nodes[-1]
    for node in reversed(nodes[:-1]):
        current = Node(node.label, condition=node.condition, children=[current])
    return current


def _normalize_children(value: Any) -> list[Node]:
    if isinstance(value, Node):
        return [value]
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"Unsupported match() case value type: {type(value)!r}")


def match(attr: str, cases: dict[Any, Any]) -> list[Node]:
    branches = []
    for case_values, child_value in cases.items():
        if isinstance(case_values, tuple):
            values = case_values
            label = "/".join(str(v) for v in values)
            condition = dc.is_in(attr, values)
        else:
            values = (case_values,)
            label = str(case_values)
            condition = dc.equals(attr, case_values)

        branches.append(Node(label, condition=condition, children=_normalize_children(child_value)))
    return branches


def walk(node: Node, x):
    """Apply the data to the decision node and return a list of walk paths."""
    if not node.condition(x):
        return []

    paths = []
    for c in node.children:
        paths.extend(walk(c, x))

    if not paths:
        return [[node.label]]

    out = []
    for path in paths:
        out.append([node.label] + path)
    return out


def _walk_condition_meta(meta: dict | None, out: dict[str, dict]) -> None:
    if not meta:
        return

    op = meta.get("op")
    attr = meta.get("attr")
    value = meta.get("value")
    values = meta.get("values")
    children = meta.get("children") or []

    if attr is not None:
        entry = out.setdefault(attr, {
            "kind": None,
            "observed_values": set(),
            "numeric_thresholds": set(),
            "ops": set(),
        })
        entry["ops"].add(op)

        if op in ("is_true", "is_false"):
            entry["kind"] = entry["kind"] or "bool"
            entry["observed_values"].update({True, False})
        elif op in ("equals", "is_in"):
            observed = [value] if op == "equals" else list(values or ())
            entry["observed_values"].update(observed)
            if observed:
                if all(isinstance(v, bool) for v in observed):
                    entry["kind"] = entry["kind"] or "bool"
                elif all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in observed):
                    entry["kind"] = entry["kind"] or "number"
                else:
                    entry["kind"] = entry["kind"] or "categorical"
        elif op in ("gt", "ge", "lt", "le"):
            entry["kind"] = entry["kind"] or "number"
            entry["numeric_thresholds"].add((op, value))

    for child in children:
        _walk_condition_meta(child, out)


def infer_schema(node: Node) -> dict[str, dict]:
    out: dict[str, dict] = {}

    def visit(n: Node):
        _walk_condition_meta(getattr(n.condition, "_dgraph_meta", None), out)
        for child in n.children:
            visit(child)

    visit(node)

    result = {}
    for attr, entry in out.items():
        result[attr] = {
            "kind": entry["kind"],
            "observed_values": sorted(entry["observed_values"], key=repr),
            "numeric_thresholds": sorted(entry["numeric_thresholds"], key=repr),
            "ops": sorted(entry["ops"]),
        }
    return result
