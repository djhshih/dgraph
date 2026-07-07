# dg DSL

A small DSL for building decision graphs in Python.

## Compiler

`bin/dot2dg.py` is used to compile `dot` files to `dg` files.

However, the labels of conditional nodes need to be curated in order
for the compiler to infer the conditions accurately.

## Core builders

- `node(label, *children)`
  - Unconditional node.
  - With no children, it is a leaf.

- `branch(label, condition, *children)`
  - Conditional node.
  - Traversed only when `condition(data)` is true.

- `chain(*items)`
  - Convenience for a linear path.
  - `chain("A", "B", "C")` is equivalent to `node("A", node("B", node("C")))`.

- `case(values, *children, label=None)`
  - Describes one alternative for `match()`.
  - `values` may be a scalar or tuple.

- `match(attr, *cases)`
  - Builds branches from simple equality/membership matching.
  - If `attr == "tags"`, a case matches when any case value is present in `data.tags`.
  - Otherwise, a case matches when `getattr(data, attr)` equals one value or is in the case tuple.

## Conditions

`branch()` accepts any callable `condition(data) -> bool`.

Common helpers live in `dgraph.condition`, e.g.
- `has(tag)`
- `has_any(*tags)`
- `has_all(*tags)`
- `gt(attr, value)`, `ge(...)`, `lt(...)`, `le(...)`
- `all_of(*conds)`, `any_of(*conds)`

## Runtime model

- A graph is a tree of `Node(label, condition, children)`.
- `walk(graph, data)` returns:
  - matching paths
  - unresolved frontier requirements

## Minimal example

```python
from dgraph.condition import has
from dgraph.graph import node, branch, chain, walk, Data

graph = node(
    "root",
    branch("HER2+", has("HER2+"), chain("Systemic treatment", "Follow-up")),
    branch("HR+", has("HR+"), node("ET [I, A]")),
)

paths, missing = walk(graph, Data({"HER2+"}))
```

## Match example

```python
from dgraph.graph import node, match, case

graph = node(
    "root",
    match(
        "kind",
        case("x", node("Use X")),
        case(("y", "z"), node("Use Y/Z")),
    ),
)
```

## Notes

- Labels are display strings; conditions control traversal.
- Multiple branches may match, producing multiple paths.
- `chain()` is best for straight-line recommendations.
- `match()` is best for simple attribute dispatch.
- For richer label logic parsing/compilation, see `dgraph.logic`.
