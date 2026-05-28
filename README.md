# decision-graph

Helpers for building, traversing, validating, and importing decision graphs.

## Package layout

- `dgraph.graph`: core graph data structures and traversal helpers
- `dgraph.condition`: reusable predicate builders for attributes and tag sets
- `dgraph.schema`: lightweight schema inference and input validation
- `dgraph.diagnostics`: graph diagnostics for cycles, shared nodes, and duplicate labels
- `dgraph.dot`: DOT parsing, analysis, graph construction, and Python source generation
- `demo/ebc`: runnable examples based on early breast cancer decision flows

## Core API

### `Data`
Base dataclass for inputs passed to graph conditions.

```python
from dgraph.graph import Data

x = Data(tags={"HR+", "HER2-", "T1", "N0"})
```

`tags` is treated as an open set of categorical markers. Demos can extend `Data`
with additional typed fields.

### `Node`
A graph node with:
- `label`
- `condition`
- `children`

### `walk(node, data)`
Evaluates the graph against input data and returns:
- matching label paths as `Path` objects
- required input names observed at the frontier of those paths

```python
paths, required = walk(graph, x)
```

## Graph construction helpers

### `node(label, *children)`
Create an unconditional node. With no children, it is a leaf.

```python
node("EBC", branch(...), branch(...))
node("ET [I, A]")
```

### `branch(label, condition, *children)`
Create a conditional node.

```python
branch("HER2+", dc.has("HER2+"), ...)
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

For most attributes, cases use equality or membership checks. For `tags`, cases use
set containment.

```python
node(
    "Biopsy",
    *match(
        "tags",
        case("pNX", slnb),
        case("pN+", bottom_branches),
    ),
)
```

## Condition helpers

Available helpers in `dgraph.condition` include:
- tag (binary) attributes
    - `has(value)`
    - `has_any(*values)`
    - `has_all(*values)`
- other attributes
    - `equals(attr, value)`
    - `gt(attr, value)`
    - `ge(attr, value)`
    - `lt(attr, value)`
    - `le(attr, value)`
- combinations
    - `all_of(*conditions)`
    - `any_of(*conditions)`

Conditions carry `attrs` metadata, which is used by traversal and schema inference.

## Schema inference and validation

### `infer_schema(node)`
Walks the graph and returns a lightweight inferred schema.

Current output is a mapping from field name to kind string:
- regular attributes are inferred as `"unknown"`
- individual tag values referenced by conditions are inferred as `"tag"`

```python
from dgraph.schema import infer_schema

schema = infer_schema(graph)
```

### `validate_data(schema, data)`
Validates input data against the inferred schema.

Current validation focuses on `tags`:
- checks that `data.tags` is a collection-like value
- reports tag values not referenced by the graph

```python
from dgraph.schema import validate_data

errors = validate_data(schema, x)
```

## Diagnostics

### `analyze_graph(root)`
Returns `GraphDiagnostics` for an in-memory graph, including:
- `roots`
- `cycles`
- `duplicate_labels`
- `shared_nodes`

```python
from dgraph.diagnostics import analyze_graph

report = analyze_graph(graph)
```

## DOT support

The `dgraph.dot` package supports importing decision graphs from DOT, inspecting the
result, and generating Python source.

### Parsing and analysis

```python
from dgraph.dot import parse_dot_with_metadata, analyze_dot_graph

parsed = parse_dot_with_metadata(dot_text)
analysis = analyze_dot_graph(parsed)
```

### Build graphs from DOT

```python
from dgraph.dot import dot_to_graph, dot_to_forest

graph = dot_to_graph(dot_text)
forest = dot_to_forest(dot_text)
```

- `dot_to_graph()` returns a single `Node`; if DOT has multiple roots it creates a
  synthetic `root`
- `dot_to_forest()` preserves multiple roots and returns metadata in
  `DotGraphBuildResult`

### Generate Python source

```python
from dgraph.dot import dot_to_source

source = dot_to_source(dot_text, graph_var="graph")
```

## Public imports

`dgraph/__init__.py` re-exports:
- condition helpers from `dgraph.condition`
- DOT helpers from `dgraph.dot`
- graph helpers from `dgraph.graph`

So simple usage can start with:

```python
from dgraph import *
```

## Demos

Use `demo.sh` from the project root so imports work without setting `PYTHONPATH`
manually.

```bash
./demo.sh demo/ebc/ebc.py
./demo.sh demo/ebc/ebc-dx.py
./demo.sh demo/ebc/ebc-aln.py
```

### `demo/ebc/ebc.py`
Treatment overview flow for early breast cancer using tag-based branching.

### `demo/ebc/ebc-dx.py`
Diagnosis and staging flow modeled as a linear `chain(...)`.

### `demo/ebc/ebc-aln.py`
Axillary lymph node management flow combining tag-based decisions, `match(...)`,
and an extended `Data` model with `positive_nodes`.


## Generate `.dg` from `.dot`

Set up your `PATH` with
```
. env.sh
```

To generate the guidelines, navigate to the `dg` subdirectory for a 
cancer type (e.g. EBC) and run `make`
```
cd data/ebc/dg
make
```

