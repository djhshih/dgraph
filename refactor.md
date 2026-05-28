## What is still wrong architecturally

Even though behavior is now better, the code structure is still fragile.

### Problem 1: `dgraph/dot/ir.py` does too much

Today one file handles:
- parsing entry point orchestration
- graph-shape traversal
- semantic IR construction
- condition inference from labels
- runtime graph emission
- source reuse/candidate analysis
- alias name generation
- Python source formatting

This is the single biggest reason regressions are easy to introduce.

A bug fix in one phase can accidentally alter assumptions used in another phase.

### Problem 2: the current IR is still partly source-driven

`IRContinuation(labels, children)` is compact, but it mixes two ideas:
- semantic continuation in the decision graph
- a convenient source emission shape

That makes it harder to reason about invariants independently from formatting.

### Problem 3: reuse analysis is implicit and structural rather than explicitly modeled

The reuse pass works, but its policy is encoded through helper traversal and signature collection logic rather than through a small explicit model like:
- candidate
- occurrence count
- containment relation
- selected alias

That makes it hard to audit and hard to evolve safely.

### Problem 4: runtime emission and source emission do not share a small common lowering model

There are effectively two parallel lowerings:
- IR -> runtime `Node`
- IR -> Python source string

They are similar, but not unified.

This creates risk that fixes land in one path but not the other.

### Problem 5: formatting and semantics are interleaved

Some helper functions conceptually belong to a pretty-printer, while others belong to semantic lowering. They live together and share traversal logic.

That increases code size and maintenance burden.

---

## Why previous fixes regressed

The regressions happened because the implementation did not have sharply separated phases.

A representative pattern was:
1. fix semantic shape at render time rather than construction time
2. add flattening or suppression logic in source emission
3. later change IR construction
4. old renderer assumptions silently become wrong

Another pattern was:
1. add reuse selection for one kind of repeated structure
2. add blocking logic to avoid redundant aliases
3. later discover a real case where nested/shared reuse is still desirable
4. patch the selection policy without a small explicit containment model

These are symptoms of missing boundaries between:
- semantic inference
- normalization
- optimization/reuse
- rendering

---

## Current invariants that should remain enforced

The following invariants reflect the current intended behavior and should remain tested.

1. A DOT terminal node must never be emitted as `branch(...)`.
2. Branch-ness comes from sibling alternatives, not merely label text.
3. Structural descendants under a branch must remain structural when graph shape says so.
4. Repeated chains may be hoisted.
5. Repeated structural subtrees may be hoisted.
6. Shared repeated terminals may still be hoisted when reused across multiple larger contexts.
7. If an alias is selected, all equivalent source occurrences should use that alias consistently.
8. Variable naming should use the shortest unambiguous prefix of label words.

---

## Recommended refactor to reduce codebase size

The best way to reduce both implementation size and output size is to separate the pipeline into smaller phases with fewer cross-cutting helpers.

## Proposed phase split

### Phase 1: DOT -> semantic graph IR

Responsibility:
- only infer semantic structure
- no source reuse decisions
- no variable naming
- no formatting

Suggested output model:
- `Structural(label, children=...)`
- `Decision(label, condition_spec, continuation=...)`
- perhaps `Sequence(labels)` if linear-path compaction is still desired

Goal:
- this phase should answer only “what graph does this DOT mean?”

### Phase 2: semantic IR -> normalized source IR

Responsibility:
- normalize all expressions into a renderable source-expression tree
- convert continuations into one consistent expression form
- make repeated-expression comparison easy

Goal:
- remove the need for ad hoc helpers like “continuation as tree” being scattered across reuse logic

### Phase 3: source IR -> reuse plan

Responsibility:
- count expressions
- build containment graph
- choose aliases explicitly
- assign short names

Suggested explicit data structure:

```python
@dataclass
class ReuseCandidate:
    signature: tuple
    expr: SourceExpr
    size: int
    count: int
    parents: set[tuple]
```

Then selection becomes a small policy module rather than several intertwined traversals.

### Phase 4: source IR + reuse plan -> rendered Python

Responsibility:
- formatting only
- no semantic decisions
- no alias discovery

This split would likely reduce code volume because many traversal helpers become phase-local and simpler.

---

## Recommended refactor to reduce output footprint

The generated output is still larger than necessary in some cases.

### Improvement 1: avoid importing unused condition helpers

Current source always emits:

```python
from dgraph.condition import all_of, has, has_all, has_any
```

Even when only `has()` is needed.

Instead, gather used condition helper names during source lowering and import only those.

This reduces output footprint and makes generated code easier to read.

### Improvement 2: unify `node(...)` and `chain(...)` emission policy

Right now chain/leaf decisions are made in several places.

A single normalization rule for “one label vs multiple labels” would reduce both code and output noise.

### Improvement 3: optionally prefer inline single-use expressions more aggressively

The output can still be made smaller by ensuring aliases are emitted only for repeated expressions with clear payoff.

A simple cost model could help:
- estimated saved characters if aliased
- estimated readability gain
- alias only if benefit > threshold

This would avoid unnecessary definitions in medium-sized graphs.

### Improvement 4: separate readability mode from minimal mode

Two source emission modes would help:
- `readable`: more aliases, more vertical formatting
- `compact`: fewer aliases, shorter output

That would prevent one heuristic from trying to satisfy conflicting goals.

---

## Recommended refactor to improve maintainability

## 1. Remove dead or stale concepts from the IR module

`IRLeaf.source_alias` is currently not carrying meaningful behavior and should either be used systematically or removed.

Similarly, helpers that remain from prior aliasing designs should be removed once a cleaner reuse layer exists.

Dead fields and half-retired mechanisms are regression magnets.

## 2. Make reuse planning explicit and testable as a pure function

A function like this would help:

```python
def plan_source_reuse(expr: SourceExpr) -> ReusePlan: ...
```

Then tests can validate the reuse plan directly instead of only validating final strings.

That would catch bugs earlier and reduce string-fragility in tests.

## 3. Introduce golden tests for representative real graphs

Small unit tests are good, but this project also needs stable high-level tests for graphs like:
- `ebc-aln`
- branching with shared subtree reuse
- branching with shared terminals
- multi-root synthetic root case

These should assert both:
- semantic equivalence (`walk`, schema)
- key source shape invariants

## 4. Add differential tests between runtime and emitted source

For every tricky case:
- build runtime graph via `dot_to_graph()`
- build source via `dot_to_source()` and `exec`
- compare behavior

Some of this exists already and should be expanded rather than kept incidental.

## 5. Shrink helper surface by introducing small local classes

Many helpers currently pass raw tuples and sets around.

A few small dataclasses would reduce cognitive load:
- `ConditionSpec`
- `ReuseCandidate`
- `ReusePlan`
- `RenderedImportSet`

This usually reduces maintenance cost even if it adds a few lines, because it removes diffuse implicit contracts.

---

## Recommended refactor to avoid “fix one bug, cause another”

## Principle 1: construction-first semantics, always

Semantic bugs must be fixed in IR construction, not patched during rendering.

Rendering should not reinterpret semantics.

## Principle 2: optimization after normalization

Reuse/aliasing is an optimization. It should happen only after semantic structure has been normalized into a stable source-expression form.

## Principle 3: formatting last

Formatting should never affect alias selection or semantic interpretation.

## Principle 4: one place for each policy

There should be exactly one place each for:
- condition inference
- branch-vs-structural inference
- reuse selection
- name generation
- import generation

Not several partially overlapping helpers.

## Principle 5: test policies directly, not just output strings

Where possible, assert intermediate plans:
- semantic IR shape
- reuse plan
- selected alias names
- used imports

That will make regressions smaller and easier to localize.

---

## Concrete cleanup plan

### Short-term

1. Update/remove stale fields like `IRLeaf.source_alias`.
2. Extract naming policy into a dedicated helper section or module.
3. Extract source reuse planning into its own pure function/module.
4. Add tests for:
   - short-name disambiguation
   - import minimization
   - `ebc-aln` key alias invariants

### Medium-term

1. Introduce a normalized source-expression layer.
2. Move all reuse logic to operate on that layer only.
3. Make `ir_to_graph()` and `ir_to_source()` lower from the same normalized semantic form.

### Long-term

1. Split `dgraph/dot/ir.py` into smaller modules, e.g.:
   - `dgraph/dot/semantic_ir.py`
   - `dgraph/dot/lower_runtime.py`
   - `dgraph/dot/lower_source.py`
   - `dgraph/dot/reuse.py`
   - `dgraph/dot/format_py.py`
2. Add a compact-vs-readable source emission mode.
3. Add end-to-end golden tests for representative real documents.

---

## Suggested target architecture

A maintainable target architecture would look roughly like:

```text
DOT text
  -> parse
  -> semantic inference
  -> semantic IR
  -> source normalization
  -> reuse planning
  -> Python rendering
```

and separately:

```text
semantic IR
  -> runtime graph lowering
```

That keeps:
- semantic meaning stable
- optimization explicit
- formatting isolated

This is the best way to reduce codebase complexity, reduce output footprint, and avoid repeating the recent pattern where one bug fix created another regression.
