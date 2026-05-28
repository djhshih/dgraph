from __future__ import annotations

from dgraph.graph import Node, branch, chain, node

from dgraph.dot.ir import DotIR, IRChild, IRContinuation, IRLeaf, IRStructuralChild, IRTree, infer_condition_from_label


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
