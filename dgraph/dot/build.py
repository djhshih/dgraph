from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

import dgraph.condition as dc
from dgraph.graph import Node, node

from .analyze import analyze_dot_graph, find_roots
from .parse import DotParseResult, parse_dot_with_metadata


@dataclass(frozen=True)
class DotGraphBuildResult:
    roots: list[Node]
    synthetic_root: bool
    node_labels: dict[str, str]
    edges: list[tuple[str, str]]
    node_order: list[str]


Condition = Callable[[object], bool]


def _normalize_tokens(parts: list[str]) -> tuple[str, ...]:
    return tuple(part.strip() for part in parts if part.strip())


def infer_condition_from_label(label: str):
    if " or " in label:
        tokens = _normalize_tokens(label.split(" or "))
        return dc.has_any(*tokens)
    if "/" in label:
        tokens = _normalize_tokens(label.split("/"))
        return dc.has_all(*tokens)
    return dc.has(label.strip())


def _node_label(node_id: str, node_labels: dict[str, str]) -> str:
    return node_labels.get(node_id, node_id)


def _is_branching(node_id: str, children_by_id: dict[str, list[str]]) -> bool:
    return len(children_by_id.get(node_id, [])) >= 2


def _child_condition(parent_id: str, child_id: str, children_by_id: dict[str, list[str]], node_labels: dict[str, str]) -> Condition | None:
    if not _is_branching(parent_id, children_by_id):
        return None
    return infer_condition_from_label(_node_label(child_id, node_labels))


def _clone_subgraph(
    node_id: str,
    node_labels: dict[str, str],
    children_by_id: dict[str, list[str]],
    branch_condition: Condition | None = None,
    cloning: set[str] | None = None,
) -> Node:
    if cloning is None:
        cloning = set()
    if node_id in cloning:
        return Node(_node_label(node_id, node_labels), condition=branch_condition or (lambda x: True), children=[])

    next_cloning = set(cloning)
    next_cloning.add(node_id)
    children = [
        _clone_subgraph(
            child_id,
            node_labels,
            children_by_id,
            branch_condition=_child_condition(node_id, child_id, children_by_id, node_labels),
            cloning=next_cloning,
        )
        for child_id in children_by_id.get(node_id, [])
    ]
    return Node(_node_label(node_id, node_labels), condition=branch_condition or (lambda x: True), children=children)


def build_graph(
    parsed_or_node_labels: DotParseResult | dict[str, str],
    edges: list[tuple[str, str]] | None = None,
    node_order: list[str] | None = None,
) -> Node | list[Node]:
    if isinstance(parsed_or_node_labels, DotParseResult):
        parsed = parsed_or_node_labels
    else:
        if edges is None:
            raise TypeError("edges is required when build_graph() is called with node labels")
        parsed = DotParseResult(parsed_or_node_labels, edges, node_order or [])

    node_ids = set(parsed.node_labels)
    for src, dst in parsed.edges:
        node_ids.add(src)
        node_ids.add(dst)

    if not node_ids:
        raise ValueError("DOT graph is empty")

    children_by_id: dict[str, list[str]] = defaultdict(list)
    for src, dst in parsed.edges:
        children_by_id[src].append(dst)

    roots = find_roots(node_ids, parsed.edges, node_order=parsed.node_order)
    if not roots:
        ordered_ids = [node_id for node_id in parsed.node_order if node_id in node_ids]
        ordered_set = set(ordered_ids)
        ordered_ids.extend(sorted(node_id for node_id in node_ids if node_id not in ordered_set))
        return [_clone_subgraph(node_id, parsed.node_labels, children_by_id) for node_id in ordered_ids]

    built_roots = [_clone_subgraph(root_id, parsed.node_labels, children_by_id) for root_id in roots]
    return built_roots if len(built_roots) > 1 else built_roots[0]


def dot_to_graph(dot_text: str) -> Node:
    parsed = parse_dot_with_metadata(dot_text)
    graph = build_graph(parsed)
    if isinstance(graph, list):
        return node("root", *graph)
    return graph


def dot_to_forest(dot_text: str) -> DotGraphBuildResult:
    parsed = parse_dot_with_metadata(dot_text)
    graph = build_graph(parsed)
    roots = graph if isinstance(graph, list) else [graph]
    analysis = analyze_dot_graph(parsed)
    return DotGraphBuildResult(
        roots=roots,
        synthetic_root=analysis.synthetic_root_required,
        node_labels=parsed.node_labels,
        edges=parsed.edges,
        node_order=parsed.node_order,
    )
