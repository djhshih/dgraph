from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import keyword
import re
from typing import TypeAlias

import dgraph.condition as dc
from dgraph.graph import Node, branch, chain, node

from dgraph.dot.analyze import find_roots
from dgraph.dot.parse import DotParseResult, parse_dot_with_metadata


@dataclass(frozen=True)
class IRLeaf:
    labels: tuple[str, ...]
    source_alias: str | None = None


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
IRExpr = IRLeaf | IRNode | IRContinuation


@dataclass(frozen=True)
class DotIR:
    roots: tuple[IRTree, ...]
    synthetic_root: bool


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


# TODO introduce logical statement parsing
def infer_condition_spec_from_label(label: str) -> tuple[str, tuple[str, ...]]:
    normalized = label.strip()
    lower = normalized.lower()
    if " and " in lower:
        parts = [part.strip() for part in normalized.split(" and ") if part.strip()]
        if len(parts) > 1:
            return "has_all", tuple(parts)
    if "/" in normalized:
        return "has_all", _normalize_tokens(normalized.split("/"))
    if " or " in lower:
        parts = [part.strip() for part in normalized.split(" or ") if part.strip()]
        if len(parts) > 1:
            return "has_any", tuple(parts)
    return "has", (normalized,)


def _quote(value: str) -> str:
    return repr(value)


def _ordered_node_ids(node_ids: set[str], node_order: list[str]) -> list[str]:
    ordered = [node_id for node_id in node_order if node_id in node_ids]
    ordered_set = set(ordered)
    return ordered + sorted(node_id for node_id in node_ids if node_id not in ordered_set)


def _node_label(node_id: str, node_labels: dict[str, str]) -> str:
    return node_labels.get(node_id, node_id)


def _name_parts(label: str) -> list[str]:
    parts = [part.lower() for part in re.findall(r"[0-9a-zA-Z]+", label)]
    return parts or ["graph"]


def _finalize_name(name: str, used: set[str]) -> str:
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


def _sanitize_name(label: str, used: set[str]) -> str:
    parts = _name_parts(label)
    for i in range(1, len(parts) + 1):
        candidate = "_".join(parts[:i])
        if candidate not in used and not keyword.iskeyword(candidate):
            return _finalize_name(candidate, used)
    return _finalize_name("_".join(parts), used)


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


def _tree_inner_signature(tree: IRTree) -> tuple:
    if isinstance(tree, IRLeaf):
        return ("leaf", tree.labels)
    return (
        "node",
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
        kind, values = infer_condition_spec_from_label(child_label)
        continuation = build_continuation_from_node(child_id, building)
        return IRBranch(child_label, kind, values, continuation)

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


def _emit_chain_expr(labels: tuple[str, ...]) -> str:
    if len(labels) == 1:
        return f"node({_quote(labels[0])})"
    args = ", ".join(_quote(label) for label in labels)
    return f"chain({args})"


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


def _collect_descendant_tree_signatures(tree: IRTree, out: set[tuple]) -> None:
    if isinstance(tree, IRLeaf):
        return
    if tree.prefix:
        out.add(("leaf", tree.prefix))
    for child in tree.children:
        _collect_child_descendant_signatures(child, out)


def _collect_child_descendant_signatures(child: IRChild, out: set[tuple]) -> None:
    if isinstance(child, IRStructuralChild):
        signature = _tree_signature(child.tree)
        out.add(signature)
        _collect_descendant_tree_signatures(child.tree, out)
        return
    _collect_continuation_descendant_signatures(child.continuation, out)


def _collect_continuation_descendant_signatures(continuation: IRContinuation | None, out: set[tuple]) -> None:
    if continuation is None:
        return
    as_tree = _continuation_as_tree(continuation)
    if as_tree is not None:
        out.add(_tree_signature(as_tree))
        _collect_descendant_tree_signatures(as_tree, out)
        return
    for child in continuation.children:
        _collect_child_descendant_signatures(child, out)


def _select_source_aliases(ir: DotIR) -> dict[tuple, str]:
    counts: Counter[tuple] = Counter()
    for root in ir.roots:
        _collect_tree_occurrences(root, counts)

    used_names = {"graph"}
    selected: dict[tuple, str] = {}
    candidates: dict[tuple, tuple[int, str, IRTree]] = {}
    descendant_parents: dict[tuple, set[tuple]] = defaultdict(set)

    def add_candidate(tree: IRTree) -> None:
        signature = _tree_signature(tree)
        if counts[signature] <= 1:
            return
        size = _tree_size(tree)
        base_name = _base_name_for_tree(tree)
        existing = candidates.get(signature)
        if existing is None or size > existing[0]:
            candidates[signature] = (size, base_name, tree)

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

    for signature, (_, _, tree) in candidates.items():
        descendants: set[tuple] = set()
        _collect_descendant_tree_signatures(tree, descendants)
        for descendant in descendants:
            if descendant in candidates:
                descendant_parents[descendant].add(signature)

    ordered = sorted(((size, base_name, signature, tree) for signature, (size, base_name, tree) in candidates.items()), key=lambda item: (-item[0], item[1]))
    for _, base_name, signature, _tree in ordered:
        parents = descendant_parents.get(signature, set())
        if parents and len(parents) == 1 and counts[signature] == counts[next(iter(parents))]:
            continue
        selected[signature] = _sanitize_name(base_name, used_names)

    return selected


def _child_to_source_expr(child: IRChild, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> str:
    if isinstance(child, IRStructuralChild):
        return _ir_to_source_expr(child.tree, source_aliases, inline_signatures=inline_signatures)
    return _branch_to_source_expr(child, source_aliases, inline_signatures=inline_signatures)


def _emit_continuation_expr(continuation: IRContinuation, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> str:
    as_tree = _continuation_as_tree(continuation)
    if as_tree is not None:
        return _ir_to_source_expr(as_tree, source_aliases, inline_signatures=inline_signatures)
    child_exprs = [_child_to_source_expr(child, source_aliases, inline_signatures=inline_signatures) for child in continuation.children]
    return "\n".join(child_exprs)


def _continuation_to_source_args(continuation: IRContinuation | None, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> list[str]:
    if continuation is None:
        return []
    if continuation.labels:
        return [_emit_continuation_expr(continuation, source_aliases, inline_signatures=inline_signatures)]
    args: list[str] = []
    for child in continuation.children:
        args.append(_child_to_source_expr(child, source_aliases, inline_signatures=inline_signatures))
    return args


def _branch_to_source_expr(branch_: IRBranch, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> str:
    child_items = [
        _quote(branch_.label),
        _condition_expr(branch_.condition_kind, branch_.condition_values),
        *_continuation_to_source_args(branch_.continuation, source_aliases, inline_signatures=inline_signatures),
    ]
    return _format_call("branch", child_items, indent=0)


def _ir_to_source_expr(tree: IRTree, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> str:
    signature = _tree_signature(tree)
    if inline_signatures is None or signature not in inline_signatures:
        alias = source_aliases.get(signature)
        if alias is not None:
            return alias

    if isinstance(tree, IRLeaf):
        return _emit_chain_expr(tree.labels)

    child_args = [_child_to_source_expr(child, source_aliases, inline_signatures=inline_signatures) for child in tree.children]
    current_expr = _format_call("node", [_quote(tree.label), *child_args], indent=0)
    for label in reversed(tree.prefix):
        current_expr = _format_call("node", [_quote(label), current_expr], indent=0)
    return current_expr


def _ir_to_source(tree: IRTree, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None, indent: int = 0) -> str:
    prefix = " " * indent
    expr = _ir_to_source_expr(tree, source_aliases, inline_signatures=inline_signatures)
    if "\n" not in expr:
        return f"{prefix}{expr}"
    return "\n".join(prefix + line if line else line for line in expr.splitlines())


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


def ir_to_source(ir: DotIR, graph_var: str = "graph") -> str:
    source_aliases = _select_source_aliases(ir)
    defs_by_name: dict[str, IRTree] = {}

    def collect_defs(tree: IRTree) -> None:
        signature = _tree_signature(tree)
        alias = source_aliases.get(signature)
        if alias is not None and alias not in defs_by_name:
            defs_by_name[alias] = tree
        if isinstance(tree, IRNode):
            for child in tree.children:
                collect_defs_child(child)

    def collect_defs_child(child: IRChild) -> None:
        if isinstance(child, IRStructuralChild):
            collect_defs(child.tree)
        elif child.continuation is not None:
            as_tree = _continuation_as_tree(child.continuation)
            if as_tree is not None:
                collect_defs(as_tree)
            else:
                for grandchild in child.continuation.children:
                    collect_defs_child(grandchild)

    for root in ir.roots:
        collect_defs(root)

    inline_signatures = set(source_aliases)
    def_lines = []
    for name, tree in sorted(defs_by_name.items(), key=lambda item: (-_tree_size(item[1]), item[0])):
        def_lines.append(f"{name} = {_ir_to_source_expr(tree, source_aliases, inline_signatures=inline_signatures)}")

    if ir.synthetic_root:
        body = "node(\n    'root',\n" + ",\n".join(_ir_to_source(root, source_aliases, indent=4) for root in ir.roots) + "\n)"
    else:
        body = _ir_to_source(ir.roots[0], source_aliases)

    parts = [
        "from dgraph.condition import all_of, has, has_all, has_any",
        "from dgraph.graph import branch, chain, node",
    ]
    if def_lines:
        parts.append("")
        parts.extend(def_lines)
    parts.append("")
    parts.append(f"{graph_var} = {body}")
    return "\n".join(parts) + "\n"
