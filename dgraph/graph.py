from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class Data:
    pass

@dataclass
class Node:
    label: str
    condition: Callable[["Data"], bool] = lambda x: True
    children: list["Node"] = field(default_factory=list)

def walk(node: Node, x):
    """Apply the data to the decision node and return a list of walk paths."""
    if not node.condition(x):
        return []

    paths = []
    for c in node.children:
        paths.extend(walk(c, x))

    if not paths:
        return [[node.label]]

    out = []
    for path in paths:
        out.append([node.label] + path)
    return out

