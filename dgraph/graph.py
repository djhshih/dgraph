from dataclasses import dataclass, field, is_dataclass
from typing import Any, Callable, TypeAlias

import dgraph.condition as dc


@dataclass
class Data:
    pass


@dataclass
class Node:
    label: str
    condition: Callable[["Data"], bool] = lambda x: True
    children: list["Node"] = field(default_factory=list)


@dataclass
class Case:
    values: tuple[Any, ...]
    children: list[Node]
    label: str | None = None


ChildInput: TypeAlias = Node | list[Node] | tuple[Node, ...]


def flat_list(*items: ChildInput) -> list[Node]:
    out: list[Node] = []
    for item in items:
        if isinstance(item, Node):
            out.append(item)
        elif isinstance(item, list):
            out.extend(item)
        elif isinstance(item, tuple):
            out.extend(item)
        else:
            raise TypeError(f"Unsupported child value type: {type(item)!r}")
    return out


def node(label: str, *children: ChildInput) -> Node:
    """Create an unconditional node. With no children, this is a leaf."""
    return Node(label, children=flat_list(*children))


def branch(label: str, condition: Callable[["Data"], bool], *children: ChildInput) -> Node:
    return Node(label, condition=condition, children=flat_list(*children))


def _coerce_node(item: str | Node) -> Node:
    if isinstance(item, Node):
        return item
    return Node(str(item))


def chain(*items: str | Node) -> Node:
    if not items:
        raise ValueError("chain() requires at least one label or node")

    nodes = [_coerce_node(item) for item in items]
    current = nodes[-1]
    for n in reversed(nodes[:-1]):
        current = Node(n.label, condition=n.condition, children=[current])
    return current


def case(values: Any, *children: ChildInput, label: str | None = None) -> Case:
    if isinstance(values, tuple):
        normalized_values = values
    else:
        normalized_values = (values,)
    return Case(values=normalized_values, children=flat_list(children), label=label)


def match(attr: str, *cases: Case) -> list[Node]:
    branches = []
    for c in cases:
        if len(c.values) == 1:
            condition = dc.equals(attr, c.values[0])
            label = c.label or str(c.values[0])
        else:
            condition = dc.is_in(attr, c.values)
            label = c.label or "/".join(str(v) for v in c.values)
        branches.append(Node(label, condition=condition, children=c.children))
    return branches

# core logic:
#
# if node is true:
#   walk down each child node
# else:
#   return
#
# but we return all viable paths
# TODO return paths of nodes instead
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


def _field_names(data: Any) -> set[str]:
    if is_dataclass(data):
        return {f.name for f in data.__dataclass_fields__.values()}
    if hasattr(data, "__dict__"):
        return set(vars(data).keys())
    return set()


def _matches_kind(value: Any, kind: str | None) -> bool:
    if value is None or kind is None:
        return True
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "categorical":
        return True
    return True


def validate_data(schema: dict[str, dict], data: Any) -> list[str]:
    errors: list[str] = []
    fields = _field_names(data)

    for attr, spec in schema.items():
        if attr not in fields:
            errors.append(f"Missing field: {attr}")
            continue

        value = getattr(data, attr)
        kind = spec.get("kind")
        observed_values = spec.get("observed_values", [])

        if not _matches_kind(value, kind):
            errors.append(f"Field {attr!r} expected kind {kind}, got value {value!r}")
            continue

        if value is not None and kind in ("bool", "categorical") and observed_values and value not in observed_values:
            errors.append(f"Field {attr!r} has unexpected value {value!r}; expected one of {observed_values!r}")

    return errors
