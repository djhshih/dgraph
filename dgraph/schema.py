def _condition_attrs(condition: Callable[["Data"], bool]) -> tuple[str, ...]:
    return getattr(condition, "attrs", ())


def infer_schema(node: Node) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    visited: set[int] = set()

    def record_condition(condition: Callable[["Data"], bool]) -> None:
        for attr in _condition_attrs(condition):
            if attr == "tags":
                predicate = getattr(condition, "predicate", None)
                closure = getattr(predicate, "__closure__", None)
                if closure:
                    for cell in closure:
                        value = cell.cell_contents
                        if isinstance(value, str):
                            out.setdefault(value, {"kind": "tag"})
                        elif isinstance(value, (tuple, list, set)):
                            for item in value:
                                if isinstance(item, str):
                                    out.setdefault(item, {"kind": "tag"})
                        elif hasattr(value, "attrs") and callable(value):
                            record_condition(value)
                        elif isinstance(value, (tuple, list)):
                            for item in value:
                                if hasattr(item, "attrs") and callable(item):
                                    record_condition(item)
                continue
            out.setdefault(attr, {"kind": "unknown"})

    def visit(n: Node) -> None:
        node_id = id(n)
        if node_id in visited:
            return
        visited.add(node_id)

        record_condition(n.condition)

        for child in n.children:
            visit(child)

    visit(node)
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
        return isinstance(value, (set, list, tuple))
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    return True


def validate_data(schema: dict[str, dict], data: Any) -> list[str]:
    errors: list[str] = []
    fields = _field_names(data)

    for attr, spec in schema.items():
        if attr in fields:
            value = getattr(data, attr)
            kind = spec.get("kind")
            if not _matches_kind(value, kind):
                errors.append(f"Field {attr!r} expected kind {kind}, got value {value!r}")

    if "tags" in fields:
        value = getattr(data, "tags")
        if isinstance(value, (set, list, tuple)):
            for item in value:
                if item not in schema:
                    errors.append(f"Unknown tag {item!r}")

    return errors


