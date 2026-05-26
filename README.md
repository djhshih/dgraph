# decision-graph

Helpers for building and traversing decision graphs.

## Core API

### `Node`
A graph node with:
- `label`
- `condition`
- `children`

### `walk(node, data)`
Evaluates the graph against input data and returns all matching label paths.

## DSL helpers

### `node(label, *children)`
Create an unconditional node. With no children, it is a leaf.

```python
node("EBC", branch(...), branch(...))
node("ET [I, A]")
```

Equivalent to:

```python
Node("EBC", children=[...])
```

### `branch(label, condition, *children)`
Create a conditional node.

```python
branch("HER2+", dc.is_true("her2_status"), ...)
```

Equivalent to:

```python
Node("HER2+", condition=dc.is_true("her2_status"), children=[...])
```

### `chain(*items)`
Build a linear path from labels or existing nodes.

```python
chain("Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment")
```

### `case(values, *children, label=None)`
Declare one categorical branch case for use with `match()`.

```python
case("pNX", slnb)
case(("cN0", "iN0"), slnb, label="cN0/iN0")
```

### `match(attr, *cases)`
Build sibling branches from categorical values.

```python
match(
    "n_status",
    case("pNX", slnb),
    case("pN+", *bottom_branches),
)
```

Grouped values are also supported:

```python
match(
    "n_status",
    case(("cN0", "iN0"), slnb, label="cN0/iN0"),
    case(("cN+", "iN+"), biopsy, label="cN+/iN+"),
)
```

`match()` returns a list of nodes, so use it as:

```python
node("Biopsy", *match(...))
```

or:

```python
branch("primary surgery indicated", cond, *match(...))
```

## Condition helpers

Available condition constructors include:
- `always()`
- `equals(attr, value)`
- `is_in(attr, values)`
- `is_true(attr)`
- `is_false(attr)`
- `gt(attr, value)`
- `ge(attr, value)`
- `lt(attr, value)`
- `le(attr, value)`
- `all_of(*conditions)`
- `any_of(*conditions)`

## Schema inference

Condition helpers attach `_dgraph_meta` metadata to returned callables. This enables approximate schema inference from a graph.

### `infer_schema(node)`
Returns a dictionary keyed by referenced field name.

Example output shape:

```python
{
    "n_status": {
        "kind": "categorical",
        "observed_values": ["cN0", "cN+", "iN0", "iN+", "pN+", "pNX"],
        "numeric_thresholds": [],
        "ops": ["equals", "is_in"],
    }
}
```

This inferred schema is based only on values and operators observed in the graph, not the full domain.

### `validate_data(schema, data)`
Validate a data object against an inferred schema.

Returns a list of error strings. An empty list means the data is compatible with the inferred schema.

Checks currently include:
- missing referenced fields
- rough kind mismatches (`bool`, `number`, `categorical`)
- unexpected values for observed boolean/categorical fields

## Demo runner

Use `demo.sh` from the project root so imports work without setting `PYTHONPATH` manually.

```
demo.sh demo/ebc/ebc-dx.py
demo.sh demo/ebc/ebc.py
demo.sh demo/ebc/ebc-aln.py
```

