"""Load decision-graph source from `.dg` files."""

from __future__ import annotations

from pathlib import Path

from dgraph.graph import Node


def load_dg(path: str | Path, graph_var: str = "graph") -> Node:
    """Execute a `.dg` file and return its graph root node."""
    path = Path(path)
    source = path.read_text()
    ns: dict[str, object] = {}
    exec(source, ns, ns)
    try:
        graph = ns[graph_var]
    except KeyError as exc:
        raise ValueError(f"{path}: no variable {graph_var!r} defined") from exc
    if not isinstance(graph, Node):
        raise TypeError(f"{path}: {graph_var!r} is {type(graph)!r}, expected Node")
    return graph
