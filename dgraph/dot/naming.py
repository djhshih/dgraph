"""Generate short, stable Python variable names for emitted source.

This file contains only naming policy.
It picks shortest safe prefix of label words, then disambiguates if needed.
"""

from __future__ import annotations

import keyword
import re


def name_parts(label: str) -> list[str]:
    parts = [part.lower() for part in re.findall(r"[0-9a-zA-Z]+", label)]
    return parts or ["graph"]


def finalize_name(name: str, used: set[str]) -> str:
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


def sanitize_name(label: str, used: set[str]) -> str:
    parts = name_parts(label)
    for i in range(1, len(parts) + 1):
        candidate = "_".join(parts[:i])
        if candidate not in used and not keyword.iskeyword(candidate):
            return finalize_name(candidate, used)
    return finalize_name("_".join(parts), used)
