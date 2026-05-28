"""Semantic DOT IR and DOT-to-IR construction.

This file owns meaning, not output format.
It infers structural nodes, decision branches, and compact linear paths
from parsed DOT input. Other files lower this IR to runtime graphs or Python source.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TypeAlias

import dgraph.condition as dc

from dgraph.dot.analyze import find_roots
from dgraph.dot.parse import DotParseResult, parse_dot_with_metadata


@dataclass(frozen=True)
class IRLeaf:
    labels: tuple[str, ...]


@dataclass(frozen=True)
class IRStructuralChild:
    tree: "IRTree"


@dataclass(frozen=True)
class IRContinuation:
    labels: tuple[str, ...] = ()
    children: tuple["IRChild", ...] = ()


@dataclass(frozen=True)
class IRBranch:
    label: str
    condition_kind: str
    condition_values: tuple[str, ...]
    continuation: IRContinuation | None = None


@dataclass(frozen=True)
class IRNode:
    label: str
    children: tuple["IRChild", ...]
    prefix: tuple[str, ...] = ()


IRTree = IRLeaf | IRNode
IRChild: TypeAlias = IRBranch | IRStructuralChild
@dataclass(frozen=True)
class ConditionSpec:
    kind: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class DotIR:
    roots: tuple[IRTree, ...]
    synthetic_root: bool


def _normalize_tokens(parts: list[str]) -> tuple[str, ...]:
    return tuple(part.strip() for part in parts if part.strip())


def infer_condition_from_label(label: str):
    spec = infer_condition_spec_from_label(label)
    if spec.kind == "has_any":
        return dc.has_any(*spec.values)
    if spec.kind == "has_all":
        return dc.has_all(*spec.values)
    if spec.kind == "all_of":
        return dc.all_of(*(dc.has(value) for value in spec.values))
    return dc.has(spec.values[0])


# TODO introduce logical statement parsing
def infer_condition_spec_from_label(label: str) -> ConditionSpec:
    normalized = label.strip()
    lower = normalized.lower()
    if " and " in lower:
        parts = [part.strip() for part in normalized.split(" and ") if part.strip()]
        if len(parts) > 1:
            return ConditionSpec("has_all", tuple(parts))
    if " or " in lower:
        parts = [part.strip() for part in normalized.split(" or ") if part.strip()]
        if len(parts) > 1:
            return ConditionSpec("has_any", tuple(parts))
    return ConditionSpec("has", (normalized,))


def _quote(value: str) -> str:
    return repr(value)


def _ordered_node_ids(node_ids: set[str], node_order: list[str]) -> list[str]:
    ordered = [node_id for node_id in node_order if node_id in node_ids]
    ordered_set = set(ordered)
    return ordered + sorted(node_id for node_id in node_ids if node_id not in ordered_set)


def _node_label(node_id: str, node_labels: dict[str, str]) -> str:
    return node_labels.get(node_id, node_id)


def _linear_path(node_id: str, children_by_id: dict[str, list[str]], building: set[str] | None = None) -> list[str]:
    if building is None:
        building = set()

    path_ids: list[str] = []
    current_id = node_id
    active = set(building)

    while True:
        path_ids.append(current_id)
        active.add(current_id)
        children = children_by_id.get(current_id, [])
        if len(children) != 1:
            break
        next_id = children[0]
        if next_id in active:
            break
        current_id = next_id

    return path_ids


def _child_signature(child: IRChild) -> tuple:
    if isinstance(child, IRStructuralChild):
        return ("structural", _tree_signature(child.tree))
    return ("branch", child.label, child.condition_kind, child.condition_values, _continuation_signature(child.continuation))


def _continuation_signature(continuation: IRContinuation | None) -> tuple:
    if continuation is None:
        return ("none",)
    return (
        "continuation",
        continuation.labels,
        tuple(_child_signature(child) for child in continuation.children),
    )


def _tree_signature(tree: IRTree) -> tuple:
    if isinstance(tree, IRLeaf):
        return ("leaf", tree.labels)
    return (
        "node",
        tree.prefix,
        tree.label,
        tuple(_child_signature(child) for child in tree.children),
    )


def dot_to_ir(parsed_or_text: DotParseResult | str) -> DotIR:
    parsed = parse_dot_with_metadata(parsed_or_text) if isinstance(parsed_or_text, str) else parsed_or_text

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
    synthetic_root = len(roots) != 1
    root_ids = roots or _ordered_node_ids(node_ids, parsed.node_order)
    def is_terminal(node_id: str) -> bool:
        return len(children_by_id.get(node_id, [])) == 0

    def build_structural_tree(node_id: str, building: set[str] | None = None) -> IRTree:
        if building is None:
            building = set()
        if node_id in building:
            return IRLeaf((_node_label(node_id, parsed.node_labels),))

        path_ids = _linear_path(node_id, children_by_id, building)
        labels = tuple(_node_label(path_id, parsed.node_labels) for path_id in path_ids)
        tail_id = path_ids[-1]
        continuation = build_continuation_from_node(tail_id, set(building) | set(path_ids))

        if continuation is None:
            return IRLeaf(labels=labels)

        all_labels = labels + continuation.labels
        if not continuation.children:
            return IRLeaf(labels=all_labels)

        if len(all_labels) > 1:
            return IRNode(label=all_labels[-1], children=continuation.children, prefix=all_labels[:-1])
        return IRNode(label=all_labels[0], children=continuation.children)

    def build_child_from_node(child_id: str, building: set[str], as_branch: bool) -> IRChild:
        if not as_branch:
            return IRStructuralChild(build_structural_tree(child_id, building))
        child_label = _node_label(child_id, parsed.node_labels)
        spec = infer_condition_spec_from_label(child_label)
        continuation = build_continuation_from_node(child_id, building)
        return IRBranch(child_label, spec.kind, spec.values, continuation)

    def build_continuation_from_node(node_id: str, building: set[str] | None = None) -> IRContinuation | None:
        if building is None:
            building = set()

        active = set(building)
        active.add(node_id)
        children = children_by_id.get(node_id, [])
        if not children:
            return None

        labels: list[str] = []
        path_ids: list[str] = []
        current_id = node_id

        while True:
            current_children = children_by_id.get(current_id, [])
            if len(current_children) != 1:
                break
            next_id = current_children[0]
            if next_id in active:
                break
            next_children = children_by_id.get(next_id, [])
            labels.append(_node_label(next_id, parsed.node_labels))
            path_ids.append(next_id)
            active.add(next_id)
            current_id = next_id
            if len(next_children) != 1:
                break

        tail_children = children_by_id.get(current_id, [])
        children_out: list[IRChild] = []
        if len(tail_children) > 1:
            child_is_branch = node_id in root_ids
            children_out.extend(build_child_from_node(child_id, active, as_branch=child_is_branch or not is_terminal(child_id)) for child_id in tail_children)

        if not labels and not children_out:
            return None
        return IRContinuation(labels=tuple(labels), children=tuple(children_out))

    roots = tuple(build_structural_tree(root_id) for root_id in root_ids)

    return DotIR(
        roots=roots,
        synthetic_root=synthetic_root,
    )


def _condition_expr(kind: str, values: tuple[str, ...]) -> str:
    args = ", ".join(_quote(value) for value in values)
    if kind == "has_any":
        return f"has_any({args})"
    if kind == "has_all":
        return f"has_all({args})"
    if kind == "all_of":
        inner = ", ".join(f"has({_quote(value)})" for value in values)
        return f"all_of({inner})"
    return f"has({args})"


def _base_name_for_tree(tree: IRTree) -> str:
    if isinstance(tree, IRLeaf):
        return tree.labels[0]
    return tree.prefix[0] if tree.prefix else tree.label


def _collect_tree_occurrences(tree: IRTree, counts: Counter[tuple]) -> None:
    counts[_tree_signature(tree)] += 1
    if isinstance(tree, IRNode):
        for child in tree.children:
            _collect_child_occurrences(child, counts)


def _collect_child_occurrences(child: IRChild, counts: Counter[tuple]) -> None:
    if isinstance(child, IRStructuralChild):
        _collect_tree_occurrences(child.tree, counts)
        return
    _collect_continuation_occurrences(child.continuation, counts)


def _continuation_as_tree(continuation: IRContinuation) -> IRTree | None:
    if continuation.labels and not continuation.children:
        return IRLeaf(labels=continuation.labels)
    if continuation.labels and continuation.children:
        if len(continuation.labels) > 1:
            return IRNode(label=continuation.labels[-1], children=continuation.children, prefix=continuation.labels[:-1])
        return IRNode(label=continuation.labels[0], children=continuation.children)
    return None


def _collect_continuation_occurrences(continuation: IRContinuation | None, counts: Counter[tuple]) -> None:
    if continuation is None:
        return
    as_tree = _continuation_as_tree(continuation)
    if as_tree is not None:
        _collect_tree_occurrences(as_tree, counts)
        return
    for child in continuation.children:
        _collect_child_occurrences(child, counts)


def _child_size(child: IRChild) -> int:
    if isinstance(child, IRStructuralChild):
        return _tree_size(child.tree)
    return 1 + _continuation_size(child.continuation)


def _tree_size(tree: IRTree) -> int:
    if isinstance(tree, IRLeaf):
        return len(tree.labels)
    return len(tree.prefix) + 1 + sum(_child_size(child) for child in tree.children)


def _continuation_size(continuation: IRContinuation | None) -> int:
    if continuation is None:
        return 0
    return len(continuation.labels) + sum(_child_size(child) for child in continuation.children)


