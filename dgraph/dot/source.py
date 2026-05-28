"""Render semantic DOT IR as Python source.

This file owns source formatting and source-only import collection.
It does not infer semantics; it only turns already-built IR into Python code.
"""

from __future__ import annotations

from dataclasses import dataclass

from dgraph.dot.ir import DotIR, IRBranch, IRChild, IRContinuation, IRLeaf, IRNode, IRStructuralChild, IRTree, _continuation_as_tree, _tree_size, _tree_signature, dot_to_ir
from dgraph.dot.parse import DotParseResult, parse_dot_with_metadata
from dgraph.dot.reuse import ReusePlan, plan_source_reuse


@dataclass(frozen=True)
class RenderedImportSet:
    condition_helpers: tuple[str, ...]
    graph_helpers: tuple[str, ...] = ("branch", "chain", "node")


def _quote(value: str) -> str:
    return repr(value)


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


def _collect_condition_helpers_from_tree(tree: IRTree, used: set[str]) -> None:
    if isinstance(tree, IRLeaf):
        return
    for child in tree.children:
        _collect_condition_helpers_from_child(child, used)


def _collect_condition_helpers_from_child(child: IRChild, used: set[str]) -> None:
    if isinstance(child, IRStructuralChild):
        _collect_condition_helpers_from_tree(child.tree, used)
        return
    used.add(child.condition_kind)
    _collect_condition_helpers_from_continuation(child.continuation, used)


def _collect_condition_helpers_from_continuation(continuation: IRContinuation | None, used: set[str]) -> None:
    if continuation is None:
        return
    for child in continuation.children:
        _collect_condition_helpers_from_child(child, used)


def collect_imports(ir: DotIR) -> RenderedImportSet:
    used: set[str] = set()
    for root in ir.roots:
        _collect_condition_helpers_from_tree(root, used)
    ordered = tuple(name for name in ("all_of", "has", "has_all", "has_any") if name in used)
    return RenderedImportSet(condition_helpers=ordered)


def _ir_to_source_expr(tree: IRTree, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> str:
    signature = _tree_signature(tree)
    if inline_signatures is None or signature not in inline_signatures:
        alias = source_aliases.get(signature)
        if alias is not None:
            return alias

    if isinstance(tree, IRLeaf):
        if len(tree.labels) == 1:
            return f"node({_quote(tree.labels[0])})"
        args = ", ".join(_quote(label) for label in tree.labels)
        return f"chain({args})"

    child_args = [_child_to_source_expr(child, source_aliases, inline_signatures=inline_signatures) for child in tree.children]
    current_expr = _format_call("node", [_quote(tree.label), *child_args], indent=0)
    for label in reversed(tree.prefix):
        current_expr = _format_call("node", [_quote(label), current_expr], indent=0)
    return current_expr


def _child_to_source_expr(child: IRChild, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> str:
    if isinstance(child, IRStructuralChild):
        return _ir_to_source_expr(child.tree, source_aliases, inline_signatures=inline_signatures)
    return _branch_to_source_expr(child, source_aliases, inline_signatures=inline_signatures)


def _continuation_to_source_args(continuation: IRContinuation | None, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> list[str]:
    if continuation is None:
        return []
    if continuation.labels:
        as_tree = _continuation_as_tree(continuation)
        if as_tree is not None:
            return [_ir_to_source_expr(as_tree, source_aliases, inline_signatures=inline_signatures)]
    return [_child_to_source_expr(child, source_aliases, inline_signatures=inline_signatures) for child in continuation.children]


def _branch_to_source_expr(branch_: IRBranch, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None) -> str:
    child_items = [
        _quote(branch_.label),
        _condition_expr(branch_.condition_kind, branch_.condition_values),
        *_continuation_to_source_args(branch_.continuation, source_aliases, inline_signatures=inline_signatures),
    ]
    return _format_call("branch", child_items, indent=0)


def _ir_to_source(tree: IRTree, source_aliases: dict[tuple, str], inline_signatures: set[tuple] | None = None, indent: int = 0) -> str:
    prefix = " " * indent
    expr = _ir_to_source_expr(tree, source_aliases, inline_signatures=inline_signatures)
    if "\n" not in expr:
        return f"{prefix}{expr}"
    return "\n".join(prefix + line if line else line for line in expr.splitlines())


def ir_to_source(ir: DotIR, graph_var: str = "graph") -> str:
    reuse_plan: ReusePlan = plan_source_reuse(ir)
    imports = collect_imports(ir)
    defs_by_name: dict[str, IRTree] = {}

    def collect_defs(tree: IRTree) -> None:
        signature = _tree_signature(tree)
        alias = reuse_plan.aliases.get(signature)
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

    inline_signatures = set(reuse_plan.aliases)
    def_lines = [
        f"{name} = {_ir_to_source_expr(tree, reuse_plan.aliases, inline_signatures=inline_signatures)}"
        for name, tree in sorted(defs_by_name.items(), key=lambda item: (-_tree_size(item[1]), item[0]))
    ]

    if ir.synthetic_root:
        body = "node(\n    'root',\n" + ",\n".join(_ir_to_source(root, reuse_plan.aliases, indent=4) for root in ir.roots) + "\n)"
    else:
        body = _ir_to_source(ir.roots[0], reuse_plan.aliases)

    parts = []
    if imports.condition_helpers:
        parts.append(f"from dgraph.condition import {', '.join(imports.condition_helpers)}")
    parts.append(f"from dgraph.graph import {', '.join(imports.graph_helpers)}")
    if def_lines:
        parts.append("")
        parts.extend(def_lines)
    parts.append("")
    parts.append(f"{graph_var} = {body}")
    return "\n".join(parts) + "\n"


def dot_to_source(dot_text: str, graph_var: str = "graph") -> str:
    parsed = parse_dot_with_metadata(dot_text)
    return dot_parsed_to_source(parsed, graph_var=graph_var)


def dot_parsed_to_source(parsed: DotParseResult, graph_var: str = "graph") -> str:
    return ir_to_source(dot_to_ir(parsed), graph_var=graph_var)
