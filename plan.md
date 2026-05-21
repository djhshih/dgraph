# Plan for implementing `dgraph/dot.py`

## Goal
Create `dgraph/dot.py` with functions that parse a DOT-format string and build a decision graph using the primitives in `dgraph/graph.py`.

The implementation should be guided by the structure of `demo/ebc/ebc.py`, while treating `data/dot/ebc.dot` only as example input syntax. Since `ebc.dot` contains mistakes, the parser should not try to repair or reinterpret incorrect graph structure beyond faithfully reading what is present.

## Scope
Implement parsing from DOT text into a `dgraph.graph.Node` tree (or forest that is normalized into a single root node where appropriate). The module should focus on structure extraction, not semantic correction.

## Relevant files
- `dgraph/graph.py`
- `demo/ebc/ebc.py`
- `data/dot/ebc.dot`

## Observations from existing code

### `dgraph/graph.py`
Available graph-building primitives:
- `Node(label, condition=lambda x: True, children=[])`
- `node(label, *children)` for unconditional nodes
- `branch(label, condition, *children)` for conditional nodes
- `chain(*items)` to create linear paths

Important constraint:
- DOT does not encode Python callables directly, but conditions can be inferred heuristically from branching structure.
- When a node has two or more children, the child labels should be interpreted as branch conditions.
- Imported graphs therefore can reconstruct useful `condition` callables for branch children, even though the original handwritten condition expressions are not preserved exactly.

### `demo/ebc/ebc.py`
The handwritten graph uses:
- one root node (`"EBC"`)
- a mixture of unconditional nodes and conditional branches
- repeated reusable chains like:
  - `Neoadjuvant therapy -> Primary surgery +/- RT -> Systemic treatment`
  - `Primary surgery +/- RT -> Systemic treatment`

This suggests DOT import should preserve:
- node labels
- parent/child relationships
- linear chains and branching structure
- inferred branch conditions derived from child labels when a parent has multiple children

### `data/dot/ebc.dot`
The DOT file shows a directed graph with:
- node IDs (`a`, `b`, `c`, ...)
- node attributes including `label`
- edges `a -> b`

Also observed:
- some labels differ from `ebc.py`
- there are structural inconsistencies and likely mistaken edges
- repeated labels exist for different node IDs

Implication:
- parsing must be by DOT node ID, not by label
- conversion to `Node` objects should preserve duplicated labels as separate nodes if they are separate DOT nodes
- no deduplication by label

## Proposed module API

Implement these functions in `dgraph/dot.py`:

### 1. `parse_dot(dot_text: str) -> tuple[dict[str, str], list[tuple[str, str]]]`
Return:
- mapping of DOT node id -> label
- list of directed edges `(src_id, dst_id)`

Responsibilities:
- parse a limited DOT subset sufficient for current files
- support node declarations like:
  - `a [label="Overview of EBC treatment", shape=box];`
- support edge declarations like:
  - `a -> b;`
- ignore global graph attributes like `rankdir=TB;`
- ignore non-label node attributes

Design choice:
- keep this function low-level and syntax-focused
- do not construct `Node` objects here

### 2. `find_roots(node_ids: set[str], edges: list[tuple[str, str]]) -> list[str]`
Return node IDs with no incoming edges.

Responsibilities:
- compute indegree from parsed edges
- return roots in stable order, ideally declaration/insertion order if available

Why needed:
- DOT may represent one tree or multiple disconnected components

### 3. `build_graph(node_labels: dict[str, str], edges: list[tuple[str, str]]) -> Node | list[Node]`
Construct `dgraph.graph.Node` objects from parsed DOT data.

Responsibilities:
- instantiate one `Node` per DOT node ID
- assign `label` from DOT label, falling back to the node ID if label is absent
- connect children according to edges
- preserve child order from edge appearance
- infer branch conditions for children of any parent with two or more children

Important behavior:
- if exactly one root exists, return that `Node`
- if multiple roots exist, either:
  - return `list[Node]`, or
  - wrap them in a synthetic root node

Preferred approach:
- return `list[Node]` from this low-level builder, and provide a higher-level helper that normalizes to one root if desired

### 4. `dot_to_graph(dot_text: str) -> Node`
High-level convenience function.

Responsibilities:
- call `parse_dot`
- build the graph
- if there is exactly one root, return it
- if there are multiple roots, wrap them in `node("DOT")` or another clearly documented synthetic root
- raise a clear error if there are zero roots, which usually means the DOT graph contains a cycle or malformed structure for tree conversion

## Parsing strategy
Use a lightweight custom parser based on regular expressions for the currently needed DOT subset.

### Parse node declarations
Recognize lines of the form:
- `id [ ... label="..." ... ];`

Extract:
- node id
- label value

Notes:
- attribute order may vary, so label extraction should search within the bracket contents
- support escaped quotes conservatively if convenient, but full DOT string parsing is probably unnecessary unless future files need it

### Parse edge declarations
Recognize lines of the form:
- `src -> dst;`

Notes:
- ignore edge attributes for now
- preserve encounter order

### Ignore
- opening/closing `digraph G {` / `}`
- graph-level attributes like `rankdir=TB;`
- node shape/style attrs other than label
- comments, if present, can be stripped simply

## Condition inference strategy

Conditions should be inferred from graph structure rather than treated as unavailable.

### Branching rule
If a node has:
- zero children: leaf node
- one child: unconditional continuation
- two or more children: each child is treated as a conditional branch

That means a parent with multiple outgoing edges represents a decision point, and each child should receive a nontrivial `condition` callable.

### Label-to-condition mapping
For each child label under a branching parent:
- default: use `dc.has(label)`
- if the label contains `" or "`: split into alternatives and use `dc.has_any(...)`
- if the label contains `/`: split into conjunctions and use `dc.has_all(...)`

Examples:
- `"HER2+"` -> `dc.has("HER2+")`
- `"cT1a or cT1b N0"` -> heuristically split on `or` and map to `dc.has_any(...)`
- `"HR+/HER2-"` -> `dc.has_all("HR+", "HER2-")`

### Normalization rules
To keep inference predictable, define a normalization helper for condition tokens:
- trim whitespace around tokens
- drop empty tokens
- preserve the original visible text otherwise

Recommendation:
- start with minimal normalization only
- avoid trying to repair malformed labels in `ebc.dot`
- keep inference faithful to the literal label text

### Parsing precedence
Use simple precedence:
1. if label contains `" or "`, interpret as `has_any(...)`
2. else if label contains `/`, interpret as `has_all(...)`
3. else use `has(...)`

This keeps behavior deterministic and easy to document.

### Important caveat
This condition inference is heuristic and label-driven:
- it will not reproduce all semantics from `demo/ebc/ebc.py`
- labels such as `"cT1a or cT1b N0"` may still require domain-specific tokenization beyond simple string splitting
- the implementation should not attempt to correct or reinterpret mistakes in `data/dot/ebc.dot`

A practical first version should therefore infer conditions only from the literal child labels according to the above rules.

## Graph construction strategy

### Internal representation
During build:
- create `Node` instances eagerly for every DOT node ID
- maintain adjacency list `children_by_id`
- attach children after all nodes are known
- assign each child node a condition inferred from its label if its parent has multiple children; otherwise leave it unconditional

### Identity handling
Because labels may repeat:
- `Node` object identity must be tied to DOT node ID, not label

### Root detection
- compute all destinations from edges
- roots are node IDs never appearing as destinations

### Cycle handling
`dgraph.graph.Node` is tree-oriented but can technically hold arbitrary object references. However, downstream traversal like `walk()` is recursive and assumes acyclic structure.

So `dgraph/dot.py` should:
- detect cycles during build or root-to-leaf validation
- raise `ValueError` for cyclic DOT input rather than creating a recursive structure that may break `walk()`

Suggested helper:
- DFS with visiting/visited states on node IDs

## Expected limitations
These should be documented in the module docstring and function docstrings:
- only supports a small DOT subset
- infers conditions heuristically from branching child labels rather than reconstructing the original handwritten Python expressions exactly
- does not correct semantic or structural mistakes in DOT input
- rejects cyclic graphs for compatibility with `dgraph.graph.walk()`
- may ignore subgraphs, ports, HTML-like labels, and advanced DOT syntax

## Suggested implementation order

1. Create `dgraph/dot.py`
2. Implement `parse_dot()`
3. Implement `find_roots()`
4. Implement a helper such as `infer_condition_from_label(label: str)` using `dgraph.condition`
5. Implement cycle detection helper
6. Implement `build_graph()` with branch-condition assignment based on sibling count
7. Implement `dot_to_graph()` convenience wrapper
8. Add clear docstrings describing limitations
9. Add a small test/demo snippet using `data/dot/ebc.dot`

## Suggested tests

### Unit tests for parsing
- parses node declarations with labels
- parses edges
- ignores graph attributes and non-label attrs
- preserves duplicate labels across different IDs

### Unit tests for build
- single-root tree converts correctly
- multi-root input returns multiple roots or a synthetic wrapper, depending on API
- missing label falls back to node ID
- child order follows edge order
- a child under a branching parent gets an inferred `has()` condition from its label
- a child label containing `or` gets an inferred `has_any()` condition
- a child label containing `/` gets an inferred `has_all()` condition
- a child under a single-child parent remains unconditional

### Validation tests
- graph with no roots raises `ValueError`
- malformed node or edge syntax raises a clear parse error or is ignored consistently, depending on chosen strictness

### EBC-based smoke test
- parse `data/dot/ebc.dot`
- confirm a graph is produced from the DOT as written
- do not compare against `demo/ebc/ebc.py` semantics, since the DOT file is known to be incorrect
- optionally assert key labels/edges that actually appear in the DOT text

## Open design questions

1. **Return type of the builder**
   - `Node` only, with synthetic root when needed

2. **Strictness of parser**
   - Unsupported syntax should raise if it interferes with node or edge
     construction
   - Recommendation: be permissive for irrelevant lines, strict for malformed node/edge lines that appear intended for supported syntax.

## Recommended final shape
A practical first version of `dgraph/dot.py` should export:
- `parse_dot`
- `find_roots`
- `infer_condition_from_label`
- `dot_to_graph`

and should assign inferred conditions to children of branching nodes based on their labels.

That keeps the implementation simple, faithful to the DOT input, and better aligned with the current `dgraph.graph` decision model.