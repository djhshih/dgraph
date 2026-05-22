from dataclasses import dataclass, field, is_dataclass
from typing import Any, Callable, TypeAlias

import dgraph.condition as dc


@dataclass
class Data:
    attr: set


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


@dataclass(frozen=True)
class GraphDiagnostics:
    roots: list[str]
    unreachable: list[str]
    cycles: list[list[str]]
    duplicate_labels: dict[str, list[str]]
    shared_nodes: list[str]


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
    if not isinstance(values, tuple):
        values = (values,)
    return Case(values=values, children=flat_list(*children), label=label)


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


def walk(node: Node, x):
    """Apply the data to the decision node and return a list of walk paths."""

    visiting: set[int] = set()

    def visit(node: Node, x):
        node_id = id(node)
        if node_id in visiting:
            return []

        if not node.condition(x):
            return []

        visiting.add(node_id)
        paths = []
        for c in node.children:
            paths.extend(visit(c, x))
        visiting.remove(node_id)

        if not paths:
            return [[node.label]]

        out = []
        for path in paths:
            out.append([node.label] + path)
        return out

    return visit(node, x)


def _condition_attrs(condition: Callable[["Data"], bool]) -> tuple[str, ...]:
    return getattr(condition, "attrs", ())


def infer_schema(node: Node) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    visited: set[int] = set()

    def visit(n: Node) -> None:
        node_id = id(n)
        if node_id in visited:
            return
        visited.add(node_id)

        for attr in _condition_attrs(n.condition):
            out.setdefault(attr, {"kind": "tag" if attr == "attr" else "unknown"})

        for child in n.children:
            visit(child)

    visit(node)
    return out


def _field_names(data: Any) -> set[str]:
    if is_dataclass(data):
        return {f.name for f in data.__dataclass_fields__.values()}
    if hasattr(data, "__dict__"):
        return set(vars(data).keys())
    return set()


def _matches_kind(value: Any, kind: str | None) -> bool:
    if value is None or kind is None:
        return True
    if kind == "tag":
        return isinstance(value, (set, list, tuple))
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    return True


def validate_data(schema: dict[str, dict], data: Any) -> list[str]:
    errors: list[str] = []
    fields = _field_names(data)

    for attr, spec in schema.items():
        if attr not in fields:
            continue

        value = getattr(data, attr)
        kind = spec.get("kind")

        if not _matches_kind(value, kind):
            errors.append(f"Field {attr!r} expected kind {kind}, got value {value!r}")

    return errors


def analyze_graph(root: Node) -> GraphDiagnostics:
    visited: set[int] = set()
    active: list[Node] = []
    active_set: set[int] = set()
    incoming: dict[int, int] = {}
    labels: dict[str, list[str]] = {}
    cycles: list[list[str]] = []

    def visit(n: Node) -> None:
        node_id = id(n)
        if node_id in active_set:
            idx = next(i for i, node in enumerate(active) if id(node) == node_id)
            cycles.append([node.label for node in active[idx:]] + [n.label])
            return
        if node_id in visited:
            return

        visited.add(node_id)
        labels.setdefault(n.label, []).append(n.label)
        active.append(n)
        active_set.add(node_id)
        for child in n.children:
            incoming[id(child)] = incoming.get(id(child), 0) + 1
            visit(child)
        active.pop()
        active_set.remove(node_id)

    visit(root)
    duplicate_labels = {label: items for label, items in labels.items() if len(items) > 1}
    shared_nodes = sorted(node.label for node in _iter_nodes(root) if incoming.get(id(node), 0) > 1)
    return GraphDiagnostics(
        roots=[root.label],
        unreachable=[],
        cycles=cycles,
        duplicate_labels=duplicate_labels,
        shared_nodes=shared_nodes,
    )


def _iter_nodes(root: Node):
    seen: set[int] = set()
    stack = [root]
    while stack:
        node = stack.pop()
        node_id = id(node)
        if node_id in seen:
            continue
        seen.add(node_id)
        yield node
        stack.extend(reversed(node.children))
