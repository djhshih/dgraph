# Plan

## Helper functions for LLM-friendly graph construction

### node
Compact helper for creating an unconditional grouping node.

```python
node(label, *children)
```

Equivalent to:

```python
Node(label, children=list(children))
```

Motivation:
- avoids special root-only construction patterns
- reduces direct use of `Node(...)` boilerplate
- gives the DSL one explicit form for unconditional grouping

### branch
Compact helper for creating a node with a condition and children.

```python
branch(label, condition, *children)
```

Equivalent to:

```python
Node(label, condition=condition, children=list(children))
```

Motivation:
- reduces boilerplate
- makes nested branching easier for an LLM to generate

### case
Helper for one categorical branch case used by `match()`.

```python
case("pNX", slnb)
case(("cN0", "iN0"), slnb, label="cN0/iN0")
```

Motivation:
- simplifies `match()` syntax
- avoids dict-based branching specifications
- allows explicit display labels for grouped categorical values

### match
Helper for branching on categorical attribute values.

```python
match(
    attr,
    case(("cN0", "iN0"), slnb, label="cN0/iN0"),
    case(("cN+", "iN+"), biopsy, label="cN+/iN+"),
)
```

Motivation:
- preserves domain-native categorical states
- discourages lossy boolean simplification
- makes guideline tables easier for an LLM to translate into code
- uses repeated `case(...)` forms rather than a dict, which is easier to generate and extend

### chain
Helper for constructing a linear path without deeply nested `children=[...]` boilerplate.

```python
chain("Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment")
```

Equivalent to nested nodes forming a single path.

Motivation:
- makes repeated treatment paths easier to express
- reduces nesting depth in generated code
- helps LLMs emit flatter, more reliable structures

## Condition metadata for schema inference

To make schema inference possible, `dgraph.condition` helpers should return callables with attached metadata describing the logical operation they represent. The callable API stays the same, but each returned function gets a `_dgraph_meta` attribute.

### Metadata shape

Each condition callable should expose:

```python
condition._dgraph_meta = {
    "op": "equals" | "is_in" | "is_true" | "is_false" | "gt" | "ge" | "lt" | "le" | "all_of" | "any_of",
    "attr": str | None,
    "value": Any | None,
    "values": tuple[Any, ...] | None,
    "children": list[dict] | None,
}
```

Not all fields are used by all operations.

### Examples

```python
equals("n_status", "pN+")
```

would attach:

```python
{
    "op": "equals",
    "attr": "n_status",
    "value": "pN+",
    "values": None,
    "children": None,
}
```

```python
is_in("n_status", ("cN0", "iN0"))
```

would attach:

```python
{
    "op": "is_in",
    "attr": "n_status",
    "value": None,
    "values": ("cN0", "iN0"),
    "children": None,
}
```

```python
all_of(is_false("postmenopausal"), is_true("receiving_ofs"))
```

would attach:

```python
{
    "op": "all_of",
    "attr": None,
    "value": None,
    "values": None,
    "children": [
        {"op": "is_false", "attr": "postmenopausal", "value": None, "values": None, "children": None},
        {"op": "is_true", "attr": "receiving_ofs", "value": None, "values": None, "children": None},
    ],
}
```

### Inference enabled by metadata

With this metadata, a graph walker can infer:
- referenced field names
- rough field kinds:
  - `is_true` / `is_false` -> boolean
  - `equals` / `is_in` with strings -> categorical
  - `gt` / `ge` / `lt` / `le` -> numeric or ordered
- observed categorical values
- observed numeric thresholds
- composite logical structure via `all_of` / `any_of`

### Notes

- The metadata represents only what is observed in the graph, not the full real-world domain schema.
- This should remain attached to the callable so existing `walk()` logic continues to work unchanged.
- A later `infer_schema(graph)` helper can traverse node conditions, read `_dgraph_meta`, and build an approximate schema automatically.
