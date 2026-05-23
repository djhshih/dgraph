from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import keyword
import re

import dgraph.condition as dc
from dgraph.graph import Node, branch, chain, node

from dgraph.dot.analyze import find_roots
from dgraph.dot.parse import DotParseResult, parse_dot_with_metadata


@dataclass(frozen=True)
class IRLeaf:
    labels: tuple[str, ...]
    alias: str | None = None
    subtree_alias: str | None = None


@dataclass(frozen=True)
class IRBranch:
    label: str
    condition_kind: str
    condition_values: tuple[str, ...]
    child: "IRTree"


@dataclass(frozen=True)
class IRNode:
    label: str
    branches: tuple[IRBranch, ...]
    prefix: tuple[str, ...] = ()
    subtree_alias: str | None = None


IRTree = IRLeaf | IRNode


@dataclass(frozen=True)
class DotIR:
    roots: tuple[IRTree, ...]
    synthetic_root: bool
    aliases: dict[tuple[str, ...], str]
    alias_labels: dict[tuple[str, ...], tuple[str, ...]]
    subtree_aliases: dict[str, str]


def _normalize_tokens(parts: list[str]) -> tuple[str, ...]:
    return tuple(part.strip() for part in parts if part.strip())


def infer_condition_from_label(label: str):
    kind, values = infer_condition_spec_from_label(label)
    if kind == "has_any":
        return dc.has_any(*values)
    if kind == "has_all":
        return dc.has_all(*values)
    if kind == "all_of":
        return dc.all_of(*(dc.has(value) for value in values))
    return dc.has(values[0])


def infer_condition_spec_from_label(label: str) -> tuple[str, tuple[str, ...]]:
    normalized = label.strip()
    lower = normalized.lower()

    if " and " in lower:
        parts = [part.strip() for part in normalized.split(" and ") if part.strip()]
        if len(parts) > 1:
            return "all_of", tuple(parts)
    if " or " in lower:
        parts = [part.strip() for part in normalized.split(" or ") if part.strip()]
        if len(parts) > 1:
            return "has_any", tuple(parts)
    if "/" in normalized:
        return "has_all", _normalize_tokens(normalized.split("/"))
    return "has", (normalized,)


def _quote(value: str) -> str:
    return repr(value)


def _ordered_node_ids(node_ids: set[str], node_order: list[str]) -> list[str]:
    ordered = [node_id for node_id in node_order if node_id in node_ids]
    ordered_set = set(ordered)
    return ordered + sorted(node_id for node_id in node_ids if node_id not in ordered_set)


def _node_label(node_id: str, node_labels: dict[str, str]) -> str:
    return node_labels.get(node_id, node_id)


def _sanitize_name(label: str, used: set[str]) -> str:
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", label).strip("_").lower()
    if not name:
        name = "graph"
    if name[0].isdigit():
        name = f"g_{name}"
    if keyword.iskeyword(name):
        name = f"{name}_graph"

    base = name
    i = 2
    while name in used:
        name = f"{base}_{i}"
        i += 1
    used.add(name)
    return name


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


def _collect_chain_counts(node_id: str, children_by_id: dict[str, list[str]], counts: Counter[tuple[str, ...]], building: set[str] | None = None) -> None:
    if building is None:
        building = set()
    if node_id in building:
        return

    path = _linear_path(node_id, children_by_id, building)
    tail_id = path[-1]
    if len(path) > 1:
        path_tuple = tuple(path)
        counts[path_tuple] += 1
        for i in range(1, len(path) - 1):
            counts[tuple(path[i:])] += 1

    next_building = set(building)
    next_building.update(path)
    for child_id in children_by_id.get(tail_id, []):
        _collect_chain_counts(child_id, children_by_id, counts, next_building)


def _gather_aliases(parsed: DotParseResult, children_by_id: dict[str, list[str]], root_ids: list[str]) -> dict[tuple[str, ...], str]:
    counts: Counter[tuple[str, ...]] = Counter()
    for root_id in root_ids:
        _collect_chain_counts(root_id, children_by_id, counts)

    aliases: dict[tuple[str, ...], str] = {}
    used_names: set[str] = {"graph"}

    repeated_paths = [path for path, count in counts.items() if count > 1]
    repeated_paths.sort(key=lambda path: (-len(path), [_node_label(node_id, parsed.node_labels) for node_id in path]))

    for path in repeated_paths:
        labels = [_node_label(node_id, parsed.node_labels) for node_id in path]
        aliases[path] = _sanitize_name(labels[0], used_names)

    return aliases


def _tree_signature(tree: IRTree) -> tuple:
    if isinstance(tree, IRLeaf):
        return ("leaf", tree.labels)
    return (
        "node",
        tree.prefix,
        tree.label,
        tuple((branch.label, branch.condition_kind, branch.condition_values, _tree_signature(branch.child)) for branch in tree.branches),
    )


def _tree_inner_signature(tree: IRTree) -> tuple:
    if isinstance(tree, IRLeaf):
        return ("leaf", tree.labels)
    return (
        "node",
        tree.label,
        tuple((branch.label, branch.condition_kind, branch.condition_values, _tree_signature(branch.child)) for branch in tree.branches),
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
    aliases = _gather_aliases(parsed, children_by_id, root_ids)
    alias_labels = {path: tuple(_node_label(node_id, parsed.node_labels) for node_id in path) for path in aliases}

    def build_ir(node_id: str, building: set[str] | None = None) -> IRTree:
        if building is None:
            building = set()
        if node_id in building:
            return IRLeaf((_node_label(node_id, parsed.node_labels),))

        path_ids = _linear_path(node_id, children_by_id, building)
        path_key = tuple(path_ids)
        tail_id = path_ids[-1]
        tail_children = children_by_id.get(tail_id, [])
        labels = tuple(_node_label(path_id, parsed.node_labels) for path_id in path_ids)

        if not tail_children:
            return IRLeaf(labels=labels, alias=aliases.get(path_key))

        next_building = set(building)
        next_building.update(path_ids)
        branches = []
        for child_id in tail_children:
            child_label = _node_label(child_id, parsed.node_labels)
            kind, values = infer_condition_spec_from_label(child_label)
            branches.append(IRBranch(child_label, kind, values, build_ir(child_id, next_building)))

        if len(labels) > 1:
            return IRNode(label=labels[-1], branches=tuple(branches), prefix=labels[:-1])
        return IRNode(label=labels[0], branches=tuple(branches))

    roots = tuple(build_ir(root_id) for root_id in root_ids)

    counts: Counter[tuple] = Counter()
    inner_counts: Counter[tuple] = Counter()

    def visit(tree: IRTree) -> None:
        counts[_tree_signature(tree)] += 1
        inner_counts[_tree_inner_signature(tree)] += 1
        if isinstance(tree, IRNode):
            for branch_ in tree.branches:
                visit(branch_.child)

    for root in roots:
        visit(root)

    used_names = {"graph", *aliases.values()}
    subtree_aliases: dict[tuple, str] = {}

    def attach_aliases(tree: IRTree) -> IRTree:
        signature = _tree_signature(tree)
        inner_signature = _tree_inner_signature(tree)
        subtree_alias = None
        should_alias = counts[signature] > 1 or (isinstance(tree, IRNode) and tree.prefix and inner_counts[inner_signature] > 1)
        if should_alias:
            if isinstance(tree, IRLeaf):
                base = tree.labels[0]
                alias_key = signature
            elif tree.prefix and inner_counts[inner_signature] > 1:
                base = tree.label
                alias_key = inner_signature
            else:
                base = tree.prefix[0] if tree.prefix else tree.label
                alias_key = signature
            subtree_alias = subtree_aliases.setdefault(alias_key, _sanitize_name(base, used_names))

        if isinstance(tree, IRLeaf):
            return IRLeaf(labels=tree.labels, alias=tree.alias, subtree_alias=subtree_alias)

        branches = tuple(
            IRBranch(branch_.label, branch_.condition_kind, branch_.condition_values, attach_aliases(branch_.child))
            for branch_ in tree.branches
        )
        return IRNode(label=tree.label, branches=branches, prefix=tree.prefix, subtree_alias=subtree_alias)

    roots = tuple(attach_aliases(root) for root in roots)

    return DotIR(
        roots=roots,
        synthetic_root=synthetic_root,
        aliases=aliases,
        alias_labels=alias_labels,
        subtree_aliases={str(signature): name for signature, name in subtree_aliases.items()},
    )


def _emit_chain_expr(labels: tuple[str, ...]) -> str:
    if len(labels) == 1:
        return f"node({_quote(labels[0])})"
    args = ", ".join(_quote(label) for label in labels)
    return f"chain({args})"


def _condition_expr(kind: str, values: tuple[str, ...]) -> str:
    args = ", ".join(_quote(value) for value in values)
    if kind == "has_any":
        return f"dc.has_any({args})"
    if kind == "has_all":
        return f"dc.has_all({args})"
    if kind == "all_of":
        inner = ", ".join(f"dc.has({_quote(value)})" for value in values)
        return f"dc.all_of({inner})"
    return f"dc.has({args})"


def _ir_to_graph(tree: IRTree) -> Node:
    if isinstance(tree, IRLeaf):
        if len(tree.labels) == 1:
            return node(tree.labels[0])
        return chain(*tree.labels)

    built_children = []
    for b in tree.branches:
        child_graph = _ir_to_graph(b.child)
        if child_graph.label == b.label:
            built_children.append(branch(b.label, infer_condition_from_label(b.label), *child_graph.children))
        else:
            built_children.append(branch(b.label, infer_condition_from_label(b.label), child_graph))
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


def _indent_block(text: str, indent: int) -> str:
    prefix = " " * indent
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def _format_call(name: str, args: list[str], indent: int = 0) -> str:
    prefix = " " * indent
    if not args:
        return f"{prefix}{name}()"
    if len(args) == 1 and "\n" not in args[0]:
        return f"{prefix}{name}({args[0]})"

    formatted_args = []
    for arg in args:
        if "\n" in arg:
            formatted_args.append(_indent_block(arg, indent + 4))
        else:
            formatted_args.append(f"{' ' * (indent + 4)}{arg}")

    return f"{prefix}{name}(\n" + ",\n".join(formatted_args) + f"\n{prefix})"


def _ir_to_source_expr(tree: IRTree, aliases: dict[tuple[str, ...], str], emitted_subtrees: set[str] | None = None) -> str:
    if isinstance(tree, IRLeaf):
        if tree.subtree_alias is not None and emitted_subtrees is not None and tree.subtree_alias in emitted_subtrees:
            return tree.subtree_alias
        if tree.alias is not None:
            return tree.alias
        return _emit_chain_expr(tree.labels)

    if tree.subtree_alias is not None and emitted_subtrees is not None and tree.subtree_alias in emitted_subtrees:
        return tree.subtree_alias

    branch_args = []
    for child in tree.branches:
        child_body = _ir_to_source_expr(child.child, aliases, emitted_subtrees=emitted_subtrees)
        if isinstance(child.child, IRLeaf) and child.child.labels and child.child.labels[0] == child.label:
            remaining = child.child.labels[1:]
            if remaining:
                child_items = [
                    _quote(child.label),
                    _condition_expr(child.condition_kind, child.condition_values),
                    _emit_chain_expr(remaining),
                ]
            else:
                child_items = [
                    _quote(child.label),
                    _condition_expr(child.condition_kind, child.condition_values),
                ]
        elif isinstance(child.child, IRNode) and not child.child.prefix and child.child.label == child.label:
            grandchild_args = []
            for grandchild in child.child.branches:
                grandchild_body = _ir_to_source_expr(grandchild.child, aliases, emitted_subtrees=emitted_subtrees)
                if isinstance(grandchild.child, IRLeaf) and grandchild.child.labels and grandchild.child.labels[0] == grandchild.label:
                    remaining = grandchild.child.labels[1:]
                    if remaining:
                        grandchild_items = [
                            _quote(grandchild.label),
                            _condition_expr(grandchild.condition_kind, grandchild.condition_values),
                            _emit_chain_expr(remaining),
                        ]
                    else:
                        grandchild_items = [
                            _quote(grandchild.label),
                            _condition_expr(grandchild.condition_kind, grandchild.condition_values),
                        ]
                else:
                    grandchild_items = [
                        _quote(grandchild.label),
                        _condition_expr(grandchild.condition_kind, grandchild.condition_values),
                        grandchild_body,
                    ]
                grandchild_args.append(_format_call("branch", grandchild_items, indent=0))
            child_items = [
                _quote(child.label),
                _condition_expr(child.condition_kind, child.condition_values),
                *grandchild_args,
            ]
        else:
            child_items = [
                _quote(child.label),
                _condition_expr(child.condition_kind, child.condition_values),
                child_body,
            ]
        branch_args.append(_format_call("branch", child_items, indent=0))

    current_expr = _format_call("node", [_quote(tree.label), *branch_args], indent=0)
    for label in reversed(tree.prefix):
        current_expr = _format_call("node", [_quote(label), current_expr], indent=0)
    return current_expr


def _ir_to_source(tree: IRTree, aliases: dict[tuple[str, ...], str], emitted_subtrees: set[str] | None = None, indent: int = 0) -> str:
    prefix = " " * indent
    expr = _ir_to_source_expr(tree, aliases, emitted_subtrees=emitted_subtrees)
    if "\n" not in expr:
        return f"{prefix}{expr}"
    return "\n".join(prefix + line if line else line for line in expr.splitlines())


def _tree_size(tree: IRTree) -> int:
    if isinstance(tree, IRLeaf):
        return len(tree.labels)
    return len(tree.prefix) + 1 + sum(1 + _tree_size(branch_.child) for branch_ in tree.branches)


def ir_to_source(ir: DotIR, graph_var: str = "graph") -> str:
    alias_lines = sorted(ir.aliases.items(), key=lambda item: item[1])
    subtree_defs_by_name: dict[str, IRTree] = {}

    def collect_subtrees(tree: IRTree) -> None:
        if isinstance(tree, IRLeaf):
            if tree.subtree_alias is not None:
                existing = subtree_defs_by_name.get(tree.subtree_alias)
                if existing is None or _tree_size(tree) > _tree_size(existing):
                    subtree_defs_by_name[tree.subtree_alias] = tree
            return
        if tree.subtree_alias is not None:
            existing = subtree_defs_by_name.get(tree.subtree_alias)
            if existing is None or _tree_size(tree) > _tree_size(existing):
                subtree_defs_by_name[tree.subtree_alias] = tree
        for branch_ in tree.branches:
            collect_subtrees(branch_.child)

    for root in ir.roots:
        collect_subtrees(root)

    subtree_defs = sorted(subtree_defs_by_name.items(), key=lambda item: (-_tree_size(item[1]), item[0]))
    claimed_names: set[str] = set()
    filtered_subtree_defs: list[tuple[str, IRTree]] = []
    for name, tree in subtree_defs:
        if name in claimed_names:
            continue
        filtered_subtree_defs.append((name, tree))
        claimed_names.add(name)
        if isinstance(tree, IRNode):
            stack = [tree]
            while stack:
                current = stack.pop()
                for branch_ in current.branches:
                    child = branch_.child
                    if getattr(child, "subtree_alias", None) is not None:
                        claimed_names.add(child.subtree_alias)
                    if isinstance(child, IRNode):
                        stack.append(child)

    subtree_defs = sorted(filtered_subtree_defs, key=lambda item: item[0])
    emitted_subtrees = {name for name, _ in subtree_defs}

    if ir.synthetic_root:
        body = "node(\n    'root',\n" + ",\n".join(_ir_to_source(root, ir.aliases, emitted_subtrees=emitted_subtrees, indent=4) for root in ir.roots) + "\n)"
    else:
        body = _ir_to_source(ir.roots[0], ir.aliases, emitted_subtrees=emitted_subtrees)

    parts = [
        "from dgraph.graph import branch, chain, node",
        "import dgraph.condition as dc",
    ]
    if alias_lines or subtree_defs:
        parts.append("")
        for path_ids, name in alias_lines:
            parts.append(f"{name} = {_emit_chain_expr(ir.alias_labels[path_ids])}")
        for name, tree in subtree_defs:
            parts.append(f"{name} = {_ir_to_source_expr(tree, ir.aliases, emitted_subtrees=set())}")
    parts.append("")
    parts.append(f"{graph_var} = {body}")
    return "\n".join(parts) + "\n"
