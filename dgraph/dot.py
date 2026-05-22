"""Parse a supported DOT subset into decision graphs.

Supported DOT features:
- directed graphs declared with ``digraph``
- one statement per line
- node statements like ``a [label="Root"]``
- edge statements like ``a -> b;`` and chained edges like ``a -> b -> c;``
- optional edge attributes, which are ignored
- quoted labels with common backslash escapes decoded via ``unicode_escape``
- ``//`` line comments outside quoted strings
- top-level graph attributes like ``rankdir=TB;``

Unsupported features raise ``ValueError``:
- subgraphs
- HTML labels
- ports
- multiline statements
- undirected edges
"""

from __future__ import annotations

import codecs
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

import dgraph.condition as dc
from dgraph.graph import Node, node


_NODE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[(.*)\]\s*;\s*$")
_EDGE_CHAIN_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)(\s*->\s*[A-Za-z_][A-Za-z0-9_]*)+\s*(?:\[.*\])?\s*;\s*$"
)
_LABEL_RE = re.compile(r'label\s*=\s*"((?:\\.|[^"\\])*)"')
_PORT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*\b")


@dataclass(frozen=True)
class DotParseResult:
    node_labels: dict[str, str]
    edges: list[tuple[str, str]]
    node_order: list[str]


@dataclass(frozen=True)
class DotGraphBuildResult:
    roots: list[Node]
    synthetic_root: bool
    node_labels: dict[str, str]
    edges: list[tuple[str, str]]
    node_order: list[str]


@dataclass(frozen=True)
class GraphAnalysis:
    roots: list[str]
    unreachable: list[str]
    cycles: list[list[str]]
    duplicate_labels: dict[str, list[str]]
    shared_nodes: list[str]
    synthetic_root_required: bool


def _strip_comment(line: str) -> str:
    in_quotes = False
    escaped = False
    out: list[str] = []

    for i, ch in enumerate(line):
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\":
            out.append(ch)
            escaped = True
            continue
        if ch == '"':
            out.append(ch)
            in_quotes = not in_quotes
            continue
        if not in_quotes and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
            break
        out.append(ch)

    return "".join(out).strip()


def _unescape_label(value: str) -> str:
    return codecs.decode(value, "unicode_escape")


def _parse_edge_chain(line: str) -> list[tuple[str, str]]:
    prefix = line.rsplit("[", 1)[0].rstrip() if "[" in line else line
    prefix = prefix[:-1].strip()
    parts = [part.strip() for part in prefix.split("->")]
    if len(parts) < 2 or any(not part for part in parts):
        raise ValueError(f"Unsupported DOT edge syntax: {line.strip()}")
    return list(zip(parts, parts[1:]))


def parse_dot(dot_text: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    result = parse_dot_with_metadata(dot_text)
    return result.node_labels, result.edges


def parse_dot_with_metadata(dot_text: str) -> DotParseResult:
    """Parse DOT text into node labels, directed edges, and declaration order."""
    node_labels: dict[str, str] = {}
    edges: list[tuple[str, str]] = []
    node_order: list[str] = []

    for raw_line in dot_text.splitlines():
        line = _strip_comment(raw_line)
        if not line:
            continue
        if line in {"{", "}"}:
            continue
        if line.startswith("digraph ") or line.startswith("graph "):
            continue
        if line.startswith("subgraph"):
            raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")
        if "<" in line or ">" in line and "->" not in line:
            if "label=<" in line:
                raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")
        if _PORT_RE.search(line):
            raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")
        if "--" in line:
            raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")
        if "->" in line:
            match = _EDGE_CHAIN_RE.match(line)
            if not match:
                raise ValueError(f"Unsupported DOT edge syntax: {raw_line.strip()}")
            edges.extend(_parse_edge_chain(line))
            continue
        if "[" in line and "]" in line:
            match = _NODE_RE.match(line)
            if not match:
                raise ValueError(f"Unsupported DOT node syntax: {raw_line.strip()}")
            node_id, attrs = match.groups()
            if node_id not in node_labels:
                node_order.append(node_id)
            label_match = _LABEL_RE.search(attrs)
            if label_match:
                node_labels[node_id] = _unescape_label(label_match.group(1))
            else:
                node_labels[node_id] = node_id
            continue
        if "=" in line and line.endswith(";"):
            continue
        raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")

    return DotParseResult(node_labels=node_labels, edges=edges, node_order=node_order)


def find_roots(node_ids: Iterable[str], edges: list[tuple[str, str]], node_order: list[str] | None = None) -> list[str]:
    """Return node ids with no incoming edges.

    Result order follows declaration order when available, otherwise lexical order.
    """
    node_ids = set(node_ids)
    destinations = {dst for _, dst in edges}
    roots = [node_id for node_id in node_ids if node_id not in destinations]
    if node_order is not None:
        ordered = [node_id for node_id in node_order if node_id in roots]
        remaining = sorted(node_id for node_id in roots if node_id not in set(ordered))
        return ordered + remaining
    return sorted(roots)


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


def _clone_node_graph(root_id: str, node_labels: dict[str, str], children_by_id: dict[str, list[str]], branch_condition=None, cloning: set[str] | None = None) -> Node:
    if cloning is None:
        cloning = set()
    if root_id in cloning:
        return Node(node_labels.get(root_id, root_id), condition=branch_condition or (lambda x: True), children=[])

    cloning = set(cloning)
    cloning.add(root_id)
    child_ids = children_by_id.get(root_id, [])
    is_branch = len(child_ids) >= 2
    children = [
        _clone_node_graph(
            child_id,
            node_labels,
            children_by_id,
            branch_condition=infer_condition_from_label(node_labels.get(child_id, child_id)) if is_branch else None,
            cloning=cloning,
        )
        for child_id in child_ids
    ]
    return Node(node_labels.get(root_id, root_id), condition=branch_condition or (lambda x: True), children=children)


def analyze_dot_graph(node_labels: dict[str, str], edges: list[tuple[str, str]], node_order: list[str] | None = None) -> GraphAnalysis:
    node_ids = set(node_labels)
    for src, dst in edges:
        node_ids.add(src)
        node_ids.add(dst)

    roots = find_roots(node_ids, edges, node_order=node_order)
    children_by_id: dict[str, list[str]] = defaultdict(list)
    incoming_count: Counter[str] = Counter()
    for src, dst in edges:
        children_by_id[src].append(dst)
        incoming_count[dst] += 1

    visited: set[str] = set()
    cycles: list[list[str]] = []
    active: list[str] = []
    active_set: set[str] = set()

    def dfs(node_id: str):
        if node_id in active_set:
            idx = active.index(node_id)
            cycles.append(active[idx:] + [node_id])
            return
        if node_id in visited:
            return
        visited.add(node_id)
        active.append(node_id)
        active_set.add(node_id)
        for child_id in children_by_id.get(node_id, []):
            dfs(child_id)
        active.pop()
        active_set.remove(node_id)

    for root in roots:
        dfs(root)

    unreachable = sorted(node_id for node_id in node_ids if node_id not in visited)
    if not roots:
        for node_id in sorted(node_ids):
            if node_id not in visited:
                dfs(node_id)
        unreachable = []

    labels_to_ids: dict[str, list[str]] = defaultdict(list)
    for node_id in node_order or sorted(node_ids):
        if node_id in node_ids:
            labels_to_ids[node_labels.get(node_id, node_id)].append(node_id)
    for node_id in sorted(node_ids):
        if (node_order is None or node_id not in node_order) and node_id not in labels_to_ids[node_labels.get(node_id, node_id)]:
            labels_to_ids[node_labels.get(node_id, node_id)].append(node_id)

    duplicate_labels = {
        label: ids for label, ids in labels_to_ids.items() if len(ids) > 1
    }
    shared_nodes = sorted(node_id for node_id, count in incoming_count.items() if count > 1)
    synthetic_root_required = len(roots) != 1

    deduped_cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()
    for cycle in cycles:
        signature = tuple(cycle)
        if signature not in seen_cycles:
            seen_cycles.add(signature)
            deduped_cycles.append(cycle)

    return GraphAnalysis(
        roots=roots,
        unreachable=unreachable,
        cycles=deduped_cycles,
        duplicate_labels=duplicate_labels,
        shared_nodes=shared_nodes,
        synthetic_root_required=synthetic_root_required,
    )


def build_graph(node_labels: dict[str, str], edges: list[tuple[str, str]], node_order: list[str] | None = None) -> Node | list[Node]:
    """Build `Node` objects from parsed DOT data.

    Shared incoming children are cloned per incoming path so branch conditions remain edge-local.
    """
    node_ids = set(node_labels)
    for src, dst in edges:
        node_ids.add(src)
        node_ids.add(dst)

    if not node_ids:
        raise ValueError("DOT graph is empty")

    children_by_id: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        children_by_id[src].append(dst)

    roots = find_roots(node_ids, edges, node_order=node_order)
    if not roots:
        ordered_ids = node_order or sorted(node_ids)
        return [_clone_node_graph(node_id, node_labels, children_by_id) for node_id in ordered_ids if node_id in node_ids]

    built_roots = [_clone_node_graph(root_id, node_labels, children_by_id) for root_id in roots]
    return built_roots if len(built_roots) > 1 else built_roots[0]


def dot_to_graph(dot_text: str) -> Node:
    """Parse DOT and return a single root Node.

    If the DOT graph has multiple roots or no roots, the result is wrapped in a
    synthetic ``root`` node so callers always receive a single entry point.
    """
    result = parse_dot_with_metadata(dot_text)
    graph = build_graph(result.node_labels, result.edges, node_order=result.node_order)
    if isinstance(graph, list):
        return node("root", *graph)
    return graph


def dot_to_forest(dot_text: str) -> DotGraphBuildResult:
    """Parse DOT and return root nodes plus metadata without synthetic wrapping."""
    result = parse_dot_with_metadata(dot_text)
    graph = build_graph(result.node_labels, result.edges, node_order=result.node_order)
    roots = graph if isinstance(graph, list) else [graph]
    analysis = analyze_dot_graph(result.node_labels, result.edges, node_order=result.node_order)
    return DotGraphBuildResult(
        roots=roots,
        synthetic_root=analysis.synthetic_root_required,
        node_labels=result.node_labels,
        edges=result.edges,
        node_order=result.node_order,
    )
