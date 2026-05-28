"""Build runtime decision-graph objects from DOT semantic IR.

This file owns runtime lowering only.
It converts semantic IR into `dgraph.graph.Node` objects and provides
public DOT-to-runtime convenience helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

from dgraph.graph import Node, branch, chain, node

from dgraph.dot.analyze import analyze_dot_graph
from dgraph.dot.ir import DotIR, IRChild, IRContinuation, IRLeaf, IRStructuralChild, IRTree, dot_to_ir, infer_condition_from_label
from dgraph.dot.parse import DotParseResult, parse_dot_with_metadata


@dataclass(frozen=True)
class DotGraphBuildResult:
    roots: list[Node]
    synthetic_root: bool
    node_labels: dict[str, str]
    edges: list[tuple[str, str]]
    node_order: list[str]


def _child_to_graph_nodes(child: IRChild) -> list[Node]:
    if isinstance(child, IRStructuralChild):
        return [_ir_to_graph(child.tree)]
    continuation_nodes = _apply_continuation_to_graph(child.continuation)
    return [branch(child.label, infer_condition_from_label(child.label), *continuation_nodes)]


def _apply_continuation_to_graph(continuation: IRContinuation | None) -> list[Node]:
    if continuation is None:
        return []
    if continuation.labels and not continuation.children:
        return [chain(*continuation.labels)]
    if continuation.labels:
        prefix_chain = chain(*continuation.labels)
        prefix_tail = prefix_chain
        while prefix_tail.children:
            prefix_tail = prefix_tail.children[0]
        built_children: list[Node] = []
        for child in continuation.children:
            built_children.extend(_child_to_graph_nodes(child))
        prefix_tail.children = built_children
        return [prefix_chain]
    built_children: list[Node] = []
    for child in continuation.children:
        built_children.extend(_child_to_graph_nodes(child))
    return built_children


def _ir_to_graph(tree: IRTree) -> Node:
    if isinstance(tree, IRLeaf):
        if len(tree.labels) == 1:
            return node(tree.labels[0])
        return chain(*tree.labels)

    built_children: list[Node] = []
    for child in tree.children:
        built_children.extend(_child_to_graph_nodes(child))
    if tree.prefix:
        prefix_chain = chain(*tree.prefix)
        prefix_tail = prefix_chain
        while prefix_tail.children:
            prefix_tail = prefix_tail.children[0]
        prefix_tail.children = [node(tree.label, *built_children)]
        return prefix_chain
    return node(tree.label, *built_children)


def ir_to_graph(ir: DotIR) -> Node | list[Node]:
    roots = [_ir_to_graph(root) for root in ir.roots]
    return roots if ir.synthetic_root else roots[0]


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
