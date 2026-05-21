"""Parse a small DOT subset into dgraph decision graphs.

This module supports a limited directed-graph DOT syntax sufficient for the
current project files. It extracts node labels and edges, detects roots and
cycles, and converts the result into `dgraph.graph.Node` objects.

Condition inference is heuristic:
- if a parent has a single child, that child remains unconditional
- if a parent has two or more children, each child is treated as a branch and
  receives a condition inferred from its own label
- labels containing ` or ` map to `dgraph.condition.has_any(...)`
- labels containing `/` map to `dgraph.condition.has_all(...)`
- all other labels map to `dgraph.condition.has(...)`

The implementation is intentionally literal and does not attempt to fix
mistakes in DOT input.
"""

from __future__ import annotations

import re
from collections import defaultdict

import dgraph.condition as dc
from dgraph.graph import Node, node


_NODE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[(.*)\]\s*;\s*$")
_EDGE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[.*\])?\s*;\s*$")
_LABEL_RE = re.compile(r'label\s*=\s*"((?:\\.|[^"\\])*)"')


def _strip_comment(line: str) -> str:
    return re.sub(r"//.*$", "", line).strip()


def _unescape_label(value: str) -> str:
    value = value.replace(r'\"', '"').replace(r'\\', '\\')
    return value


def parse_dot(dot_text: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Parse DOT text into node labels and directed edges."""
    node_labels: dict[str, str] = {}
    edges: list[tuple[str, str]] = []

    for raw_line in dot_text.splitlines():
        line = _strip_comment(raw_line)
        if not line:
            continue
        if line in {"{", "}"}:
            continue
        if line.startswith("digraph ") or line.startswith("graph "):
            continue
        if "->" in line:
            match = _EDGE_RE.match(line)
            if not match:
                raise ValueError(f"Unsupported DOT edge syntax: {raw_line.strip()}")
            edges.append((match.group(1), match.group(2)))
            continue
        if "[" in line and "]" in line:
            match = _NODE_RE.match(line)
            if not match:
                raise ValueError(f"Unsupported DOT node syntax: {raw_line.strip()}")
            node_id, attrs = match.groups()
            label_match = _LABEL_RE.search(attrs)
            if label_match:
                node_labels[node_id] = _unescape_label(label_match.group(1))
            else:
                node_labels[node_id] = node_id
            continue
        if "=" in line and line.endswith(";"):
            continue
        raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")

    return node_labels, edges


def find_roots(node_ids: set[str], edges: list[tuple[str, str]]) -> list[str]:
    """Return node ids with no incoming edges.

    Result order is stable and sorted by node id.
    """
    destinations = {dst for _, dst in edges}
    return [node_id for node_id in sorted(node_ids) if node_id not in destinations]


def _normalize_tokens(parts: list[str]) -> tuple[str, ...]:
    return tuple(part.strip() for part in parts if part.strip())


def infer_condition_from_label(label: str):
    """Infer a condition from a branch label.

    Precedence:
    1. ` or ` -> has_any
    2. `/` -> has_all
    3. default -> has
    """
    if " or " in label:
        tokens = _normalize_tokens(label.split(" or "))
        return dc.has_any(*tokens)
    if "/" in label:
        tokens = _normalize_tokens(label.split("/"))
        return dc.has_all(*tokens)
    return dc.has(label.strip())


def _detect_cycles(node_ids: set[str], edges: list[tuple[str, str]]) -> None:
    children_by_id: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        children_by_id[src].append(dst)

    state: dict[str, int] = {node_id: 0 for node_id in node_ids}

    def visit(node_id: str) -> None:
        if state[node_id] == 1:
            raise ValueError("DOT graph contains a cycle")
        if state[node_id] == 2:
            return
        state[node_id] = 1
        for child_id in children_by_id[node_id]:
            visit(child_id)
        state[node_id] = 2

    for node_id in node_ids:
        if state[node_id] == 0:
            visit(node_id)


def build_graph(node_labels: dict[str, str], edges: list[tuple[str, str]]) -> Node | list[Node]:
    """Build `Node` objects from parsed DOT data."""
    node_ids = set(node_labels)
    for src, dst in edges:
        node_ids.add(src)
        node_ids.add(dst)

    if not node_ids:
        raise ValueError("DOT graph is empty")

    _detect_cycles(node_ids, edges)

    children_by_id: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        children_by_id[src].append(dst)

    dot_nodes = {
        node_id: Node(node_labels.get(node_id, node_id))
        for node_id in node_ids
    }

    for parent_id, child_ids in children_by_id.items():
        is_branch = len(child_ids) >= 2
        children: list[Node] = []
        for child_id in child_ids:
            child = dot_nodes[child_id]
            if is_branch:
                children.append(Node(child.label, condition=infer_condition_from_label(child.label), children=child.children))
            else:
                children.append(child)
        dot_nodes[parent_id].children = children

    roots = find_roots(node_ids, edges)
    if not roots:
        raise ValueError("DOT graph has no roots")

    return [dot_nodes[root_id] for root_id in roots] if len(roots) > 1 else dot_nodes[roots[0]]


def dot_to_graph(dot_text: str) -> Node:
    """Parse DOT and return a single root Node.

    If multiple roots exist, they are wrapped in a synthetic `DOT` root.
    """
    node_labels, edges = parse_dot(dot_text)
    graph = build_graph(node_labels, edges)
    if isinstance(graph, list):
        return node("DOT", *graph)
    return graph
