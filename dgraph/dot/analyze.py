from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from .parse import DotParseResult


@dataclass(frozen=True)
class GraphAnalysis:
    roots: list[str]
    unreachable: list[str]
    cycles: list[list[str]]
    duplicate_labels: dict[str, list[str]]
    shared_nodes: list[str]
    synthetic_root_required: bool


def find_roots(node_ids: Iterable[str], edges: list[tuple[str, str]], node_order: list[str] | None = None) -> list[str]:
    node_id_set = set(node_ids)
    destinations = {dst for _, dst in edges}
    roots = [node_id for node_id in node_id_set if node_id not in destinations]
    if node_order is None:
        return sorted(roots)

    ordered = [node_id for node_id in node_order if node_id in roots]
    ordered_set = set(ordered)
    return ordered + sorted(node_id for node_id in roots if node_id not in ordered_set)


def _ordered_node_ids(node_ids: set[str], node_order: list[str] | None) -> list[str]:
    if node_order is None:
        return sorted(node_ids)
    ordered = [node_id for node_id in node_order if node_id in node_ids]
    ordered_set = set(ordered)
    return ordered + sorted(node_id for node_id in node_ids if node_id not in ordered_set)


def _dedupe_cycles(cycles: list[list[str]]) -> list[list[str]]:
    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for cycle in cycles:
        signature = tuple(cycle)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(cycle)
    return deduped


def analyze_dot_graph(
    parsed_or_node_labels: DotParseResult | dict[str, str],
    edges: list[tuple[str, str]] | None = None,
    node_order: list[str] | None = None,
) -> GraphAnalysis:
    if isinstance(parsed_or_node_labels, DotParseResult):
        parsed = parsed_or_node_labels
    else:
        if edges is None:
            raise TypeError("edges is required when analyze_dot_graph() is called with node labels")
        parsed = DotParseResult(parsed_or_node_labels, edges, node_order or [])

    node_ids = set(parsed.node_labels)
    for src, dst in parsed.edges:
        node_ids.add(src)
        node_ids.add(dst)

    roots = find_roots(node_ids, parsed.edges, node_order=parsed.node_order)
    children_by_id: dict[str, list[str]] = defaultdict(list)
    incoming_count: Counter[str] = Counter()
    for src, dst in parsed.edges:
        children_by_id[src].append(dst)
        incoming_count[dst] += 1

    visited: set[str] = set()
    cycles: list[list[str]] = []
    active: list[str] = []
    active_set: set[str] = set()

    def dfs(node_id: str) -> None:
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
    for node_id in _ordered_node_ids(node_ids, parsed.node_order):
        labels_to_ids[parsed.node_labels.get(node_id, node_id)].append(node_id)

    duplicate_labels = {label: ids for label, ids in labels_to_ids.items() if len(ids) > 1}
    shared_nodes = sorted(node_id for node_id, count in incoming_count.items() if count > 1)

    return GraphAnalysis(
        roots=roots,
        unreachable=unreachable,
        cycles=_dedupe_cycles(cycles),
        duplicate_labels=duplicate_labels,
        shared_nodes=shared_nodes,
        synthetic_root_required=len(roots) != 1,
    )
