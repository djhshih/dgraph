from dataclasses import dataclass, field
from typing import Any, Callable, Collection, TypeAlias

import dgraph.condition as dc


@dataclass
class Data:
    tags: set[str]

@dataclass
class Node:
    label: str
    condition: Callable[["Data"], bool] = lambda x: True
    children: list["Node"] = field(default_factory=list)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        return (
            self.label == other.label
            and self.children == other.children
            and getattr(self.condition, "attrs", ()) == getattr(other.condition, "attrs", ())
        )

@dataclass
class Path:
    path: list["Node"]

    def append(self, node: Node):
        self.path.append(node)

    def __iter__(self):
        for x in self.path:
            yield x

    def __eq__(self, other):
        if isinstance(other, Path):
            return self.path == other.path
        if isinstance(other, list):
            return [n.label for n in self.path] == other
        return NotImplemented

    def __add__(self, other: "Path") -> "Path":
        return Path(self.path + other.path)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return ' -> '.join(n.label for n in self.path)

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
    if not isinstance(values, tuple):
        values = (values,)
    return Case(values=values, children=flat_list(*children), label=label)


def match(attr: str, *cases: Case) -> list[Node]:
    branches = []
    for c in cases:
        if attr == "tags":
            # tags is an open set of attributes of any length
            condition = dc.contains_any(attr, c.values)
        else:
            # expect x["attr"] to be scalar
            if len(c.values) == 1:
                condition = dc.equals(attr, c.values[0])
            else:
                condition = dc.is_in(attr, c.values)
        label = c.label or (str(c.values[0]) if len(c.values) == 1 else " | ".join(str(v) for v in c.values))
        branches.append(Node(label, condition=condition, children=c.children))
    return branches


def walk(node: Node, x: Data) -> tuple[list[Path], list[Any]]:
    """Apply data x to the decision node.

    Returns a tuple of:
    - matching paths
    - required inputs observed at the frontier of those paths
    """

    visiting: set[int] = set()

    def visit(node: Node, x: Data):
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
            return [Path([node])]

        out = []
        for path in paths:
            out.append(Path([node]) + path)
        return out

    # find required attributes at end of paths
    paths = visit(node, x)
    required = []
    for p in paths:
        if len(p.path) > 0:
            node = p.path[-1]
            for c in node.children:
                a = getattr(c.condition, "attrs")
                if not a:
                    continue
                required.extend(a)

    return (paths, required)

