from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dgraph.dot.ir import DotIR, IRBranch, IRChild, IRContinuation, IRLeaf, IRNode, IRTree


@dataclass(frozen=True)
class ReuseCandidate:
    signature: tuple
    expr: "IRTree"
    size: int
    count: int
    parents: frozenset[tuple]
    base_name: str


@dataclass(frozen=True)
class ReusePlan:
    aliases: dict[tuple, str]
    candidates: tuple[ReuseCandidate, ...]


def plan_source_reuse(ir: "DotIR") -> ReusePlan:
    from dgraph.dot.ir import (
        _base_name_for_tree,
        _collect_tree_occurrences,
        _continuation_as_tree,
        _sanitize_name,
        _tree_signature,
        _tree_size,
        IRLeaf,
        IRNode,
        IRStructuralChild,
    )

    counts: Counter[tuple] = Counter()
    for root in ir.roots:
        _collect_tree_occurrences(root, counts)

    candidates_by_signature: dict[tuple, tuple[int, str, IRTree]] = {}
    descendant_parents: dict[tuple, set[tuple]] = defaultdict(set)

    def collect_descendants(tree: IRTree, out: set[tuple]) -> None:
        if isinstance(tree, IRLeaf):
            return
        if tree.prefix:
            out.add(("leaf", tree.prefix))
        for child in tree.children:
            collect_child_descendants(child, out)

    def collect_child_descendants(child: IRChild, out: set[tuple]) -> None:
        if isinstance(child, IRStructuralChild):
            signature = _tree_signature(child.tree)
            out.add(signature)
            collect_descendants(child.tree, out)
            return
        collect_continuation_descendants(child.continuation, out)

    def collect_continuation_descendants(continuation: IRContinuation | None, out: set[tuple]) -> None:
        if continuation is None:
            return
        as_tree = _continuation_as_tree(continuation)
        if as_tree is not None:
            out.add(_tree_signature(as_tree))
            collect_descendants(as_tree, out)
            return
        for child in continuation.children:
            collect_child_descendants(child, out)

    def add_candidate(tree: IRTree) -> None:
        signature = _tree_signature(tree)
        if counts[signature] <= 1:
            return
        size = _tree_size(tree)
        base_name = _base_name_for_tree(tree)
        existing = candidates_by_signature.get(signature)
        if existing is None or size > existing[0]:
            candidates_by_signature[signature] = (size, base_name, tree)

    def gather(tree: IRTree) -> None:
        add_candidate(tree)
        if isinstance(tree, IRNode):
            for child in tree.children:
                gather_child(child)

    def gather_child(child: IRChild) -> None:
        if isinstance(child, IRStructuralChild):
            gather(child.tree)
        elif child.continuation is not None:
            as_tree = _continuation_as_tree(child.continuation)
            if as_tree is not None:
                gather(as_tree)
            else:
                for grandchild in child.continuation.children:
                    gather_child(grandchild)

    for root in ir.roots:
        gather(root)

    for signature, (_, _, tree) in candidates_by_signature.items():
        descendants: set[tuple] = set()
        collect_descendants(tree, descendants)
        for descendant in descendants:
            if descendant in candidates_by_signature:
                descendant_parents[descendant].add(signature)

    ordered = sorted(
        ((size, base_name, signature, tree) for signature, (size, base_name, tree) in candidates_by_signature.items()),
        key=lambda item: (-item[0], item[1]),
    )

    used_names = {"graph"}
    aliases: dict[tuple, str] = {}
    materialized: list[ReuseCandidate] = []
    for size, base_name, signature, tree in ordered:
        parents = descendant_parents.get(signature, set())
        if parents and len(parents) == 1 and counts[signature] == counts[next(iter(parents))]:
            continue
        alias = _sanitize_name(base_name, used_names)
        aliases[signature] = alias
        materialized.append(
            ReuseCandidate(
                signature=signature,
                expr=tree,
                size=size,
                count=counts[signature],
                parents=frozenset(parents),
                base_name=base_name,
            )
        )

    return ReusePlan(aliases=aliases, candidates=tuple(materialized))
