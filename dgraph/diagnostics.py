# FIXME Is this useful?

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dgraph.graph import Node

@dataclass(frozen=True)
class GraphDiagnostics:
    roots: list[str]
    unreachable: list[str]
    cycles: list[list[str]]
    duplicate_labels: dict[str, list[str]]
    shared_nodes: list[str]

def analyze_graph(root: "Node") -> GraphDiagnostics:
    visited: set[int] = set()
    active: list["Node"] = []
    active_set: set[int] = set()
    incoming: dict[int, int] = {}
    labels: dict[str, list[str]] = {}
    cycles: list[list[str]] = []

    def visit(n: "Node") -> None:
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

def _iter_nodes(root: "Node"):
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

