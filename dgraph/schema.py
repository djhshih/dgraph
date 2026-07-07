from dataclasses import is_dataclass
from typing import Any, Callable

from dgraph.graph import Node


def _condition_attrs(condition: Callable[["Data"], bool]) -> tuple[Any, ...]:
    return getattr(condition, "attrs", ())


def _record_tag_values(out: dict[str, str], value: Any) -> None:
    if isinstance(value, str):
        out[value] = "tag"
    elif isinstance(value, (tuple, list, set)):
        for item in value:
            if isinstance(item, str):
                out[item] = "tag"


def infer_schema(node: Node) -> dict[str, str]:
    out: dict[str, str] = {}
    visited: set[int] = set()

    def record_condition(condition: Callable[["Data"], bool]) -> None:
        attrs = _condition_attrs(condition)
        predicate = getattr(condition, "predicate", None)
        closure_values = [cell.cell_contents for cell in (getattr(predicate, "__closure__", None) or ())]

        is_tag_condition = (
            "tags" in attrs
            or any(isinstance(attr, (tuple, list, set)) for attr in attrs)
            or "tags" in closure_values
        )
        if is_tag_condition:
            for attr in attrs:
                if isinstance(attr, (tuple, list, set)):
                    _record_tag_values(out, attr)
                elif isinstance(attr, str) and attr != "tags":
                    _record_tag_values(out, attr)

            for value in closure_values:
                if hasattr(value, "attrs") and callable(value):
                    record_condition(value)
                elif value != "tags":
                    _record_tag_values(out, value)
            return

        for attr in attrs:
            if isinstance(attr, str):
                out.setdefault(attr, "unknown")

        predicate = getattr(condition, "predicate", None)
        closure = getattr(predicate, "__closure__", None) or ()
        for cell in closure:
            value = cell.cell_contents
            if hasattr(value, "attrs") and callable(value):
                record_condition(value)
            elif isinstance(value, (tuple, list)):
                for item in value:
                    if hasattr(item, "attrs") and callable(item):
                        record_condition(item)

    def visit(n: Node) -> None:
        node_id = id(n)
        if node_id in visited:
            return
        visited.add(node_id)

        record_condition(n.condition)

        for child in n.children:
            visit(child)

    visit(node)
    out.pop("tags", None)
    return out


def _field_names(data: Any) -> set[str]:
    if is_dataclass(data):
        return {f.name for f in data.__dataclass_fields__.values()}
    if hasattr(data, "__dict__"):
        return set(vars(data).keys())
    return set()


def _matches_kind(value: Any, kind: str | None) -> bool:
    if value is None or kind is None:
        return True
    if kind == "tag":
        return isinstance(value, (set, frozenset, list, tuple))
    return True


def validate_data(schema: dict[str, str], data: Any) -> list[str]:
    errors: list[str] = []
    fields = _field_names(data)

    tag_names = {name for name, kind in schema.items() if kind == "tag"}

    if "tags" in fields:
        value = getattr(data, "tags")
        if not _matches_kind(value, "tag"):
            errors.append(f"Field 'tags' expected kind tag, got value {value!r}")
        elif tag_names:
            for item in value:
                if item not in tag_names:
                    errors.append(f"Unknown tag {item!r}")

    return errors


