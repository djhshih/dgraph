from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import dgraph.graph as dg


def load_patient_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load patient fixture cases from a JSON file.

    Expected shapes:
    - {"cases": [{"id": "...", "tags": [...], ...}, ...]}
    - [{"id": "...", "tags": [...], ...}, ...]
    """
    path = Path(path)
    raw = json.loads(path.read_text())
    if isinstance(raw, dict) and "cases" in raw:
        cases = raw["cases"]
    elif isinstance(raw, list):
        cases = raw
    else:
        raise ValueError(f"Unsupported patient file shape in {path}")

    if not isinstance(cases, list):
        raise TypeError(f"{path}: 'cases' must be a list")

    return cases


def case_by_id(cases: Iterable[dict[str, Any]], case_id: str) -> dict[str, Any]:
    for c in cases:
        if c.get("id") == case_id:
            return c
    raise KeyError(f"Unknown case id {case_id!r}")


def build_patient(schema: dict[str, str], case: dict[str, Any]) -> dg.Data:
    """Build a `dg.Data` instance for `walk()`/`validate_data()`.

    - `tags` are stored in `dg.Data.tags`
    - all schema attributes of kind != "tag" are set on the instance, defaulting to None
      (conditions use `getattr(x, attr)` without defaults, so we must create the attribute).
    """
    tags = set(case.get("tags", []) or [])
    x = dg.Data(tags=tags)

    for attr, kind in schema.items():
        if kind == "tag":
            continue
        # dg tests rely on numeric fields being present even when None.
        setattr(x, attr, case.get(attr, None))

    return x

