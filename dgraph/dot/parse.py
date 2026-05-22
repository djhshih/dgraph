from __future__ import annotations

import codecs
import re
from dataclasses import dataclass


_NODE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[(.*)\]\s*;\s*$")
_EDGE_CHAIN_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)(\s*->\s*[A-Za-z_][A-Za-z0-9_]*)+\s*(?:\[.*\])?\s*;\s*$"
)
_LABEL_RE = re.compile(r'label\s*=\s*"((?:\\.|[^"\\])*)"')
_PORT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*\b")


@dataclass(frozen=True)
class DotParseResult:
    node_labels: dict[str, str]
    edges: list[tuple[str, str]]
    node_order: list[str]


def _strip_comment(line: str) -> str:
    in_quotes = False
    escaped = False
    out: list[str] = []

    for i, ch in enumerate(line):
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\":
            out.append(ch)
            escaped = True
            continue
        if ch == '"':
            out.append(ch)
            in_quotes = not in_quotes
            continue
        if not in_quotes and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
            break
        out.append(ch)

    return "".join(out).strip()


def _unescape_label(value: str) -> str:
    return codecs.decode(value, "unicode_escape")


def _parse_edge_chain(line: str) -> list[tuple[str, str]]:
    prefix = line.rsplit("[", 1)[0].rstrip() if "[" in line else line
    prefix = prefix[:-1].strip()
    parts = [part.strip() for part in prefix.split("->")]
    if len(parts) < 2 or any(not part for part in parts):
        raise ValueError(f"Unsupported DOT edge syntax: {line.strip()}")
    return list(zip(parts, parts[1:]))


def parse_dot(dot_text: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    result = parse_dot_with_metadata(dot_text)
    return result.node_labels, result.edges


def parse_dot_with_metadata(dot_text: str) -> DotParseResult:
    node_labels: dict[str, str] = {}
    edges: list[tuple[str, str]] = []
    node_order: list[str] = []

    for raw_line in dot_text.splitlines():
        line = _strip_comment(raw_line)
        if not line:
            continue
        if line in {"{", "}"}:
            continue
        if line.startswith("digraph ") or line.startswith("graph "):
            continue
        if line.startswith("subgraph"):
            raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")
        if "<" in line or ">" in line and "->" not in line:
            if "label=<" in line:
                raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")
        if _PORT_RE.search(line):
            raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")
        if "--" in line:
            raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")
        if "->" in line:
            match = _EDGE_CHAIN_RE.match(line)
            if not match:
                raise ValueError(f"Unsupported DOT edge syntax: {raw_line.strip()}")
            edges.extend(_parse_edge_chain(line))
            continue
        if "[" in line and "]" in line:
            match = _NODE_RE.match(line)
            if not match:
                raise ValueError(f"Unsupported DOT node syntax: {raw_line.strip()}")
            node_id, attrs = match.groups()
            if node_id not in node_labels:
                node_order.append(node_id)
            label_match = _LABEL_RE.search(attrs)
            if label_match:
                node_labels[node_id] = _unescape_label(label_match.group(1))
            else:
                node_labels[node_id] = node_id
            continue
        if "=" in line and line.endswith(";"):
            continue
        raise ValueError(f"Unsupported DOT syntax: {raw_line.strip()}")

    return DotParseResult(node_labels=node_labels, edges=edges, node_order=node_order)
