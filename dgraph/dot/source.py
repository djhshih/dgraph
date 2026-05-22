from __future__ import annotations

from dgraph.dot.ir import dot_to_ir, ir_to_source
from dgraph.dot.parse import DotParseResult, parse_dot_with_metadata


def dot_to_source(dot_text: str, graph_var: str = "graph") -> str:
    parsed = parse_dot_with_metadata(dot_text)
    return dot_parsed_to_source(parsed, graph_var=graph_var)


def dot_parsed_to_source(parsed: DotParseResult, graph_var: str = "graph") -> str:
    return ir_to_source(dot_to_ir(parsed), graph_var=graph_var)
