from __future__ import annotations

from dataclasses import dataclass

from dgraph.graph import Node, node

from dgraph.dot.analyze import analyze_dot_graph
from dgraph.dot.ir import dot_to_ir, infer_condition_from_label
from dgraph.dot.runtime import ir_to_graph
from dgraph.dot.parse import DotParseResult, parse_dot_with_metadata


@dataclass(frozen=True)
class DotGraphBuildResult:
    roots: list[Node]
    synthetic_root: bool
    node_labels: dict[str, str]
    edges: list[tuple[str, str]]
    node_order: list[str]


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

    return ir_to_graph(dot_to_ir(parsed))


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
