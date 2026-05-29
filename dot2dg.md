# DOT node construction and `.dg` emission: current behavior and cleanup plan

This document describes the **current** DOT-to-IR and DOT-to-`.dg` behavior in the codebase, the invariants now enforced by tests, and the main opportunities to simplify the implementation so future bug fixes do not cascade into regressions.

---

## Executive summary

The current implementation in `dgraph/dot/ir.py` now does three important things correctly:

1. distinguishes **structural nodes** from **decision branches**
2. preserves the rule that **terminal DOT nodes are never emitted as decision branches**
3. performs source-level reuse selection for repeated structural expressions, including:
   - repeated chains
   - repeated subtrees
   - repeated terminal nodes reused across larger aliased contexts

However, the implementation is still more complex and more tightly coupled than it should be.

The main maintainability problem is that too much behavior still spans multiple concerns:
- DOT graph-shape interpretation
- semantic IR construction
- runtime graph construction in `dgraph.dot.interpret`
- `.dg` source emission in `dgraph.dot.compile`
- source-expression normalization through `dgraph.logic.compile`
- alias/reuse analysis
- variable naming

That coupling is why fixing one bug previously caused regressions elsewhere.

---

## Core semantic distinction

There are two different semantic roles in the generated DSL:

- **structural nodes**: emitted as `node(...)` or `chain(...)`
- **decision nodes**: emitted as `branch(label, condition, ...)`

These must not be conflated.

---

## Critical invariant

**Terminal DOT nodes are never decision nodes.**

If a DOT node has no outgoing edges, it must be emitted structurally.

So this DOT:

```dot
a -> b
b [label="RT (axilla) [II, B]"]
```

must produce:

```python
node("RT (axilla) [II, B]")
```

not:

```python
branch("RT (axilla) [II, B]", has("RT (axilla) [II, B]"))
```

This is now part of the intended semantics and should be treated as a non-negotiable invariant.

---

## Current inference model in code

The current code uses these IR types:

- `IRLeaf(labels)`
- `IRNode(label, children, prefix=...)`
- `IRBranch(label, condition_kind, condition_values, continuation)`
- `IRContinuation(labels, children)`
- `IRStructuralChild(tree)`

And these distinctions matter:

### Structural tree
A structural tree is an `IRLeaf` or `IRNode`.

### Child under a node/continuation
A child may be either:
- `IRStructuralChild` for structural descendants
- `IRBranch` for decision alternatives

This distinction is what fixed the earlier terminal-node bug.

---

## Current practical rules

## Rule A: outgoing degree 0 => structural terminal

A node with no outgoing edges becomes a structural terminal.

## Rule B: outgoing degree 1 => structural continuation

Linear paths are merged into structural chains/prefixes.

## Rule C: sibling fan-out may create decision alternatives

A node becomes a branch label only when selected as one of multiple alternatives from the same parent context.

## Rule D: descendants under a chosen branch are inferred by shape again

Once a branch is taken:
- terminal descendants remain structural
- linear descendants remain structural continuation
- later fan-out may create later branch alternatives

This avoids the old bug where all post-fan-out children were forced into `branch(...)`.

---

## Current source reuse behavior

The current source generator uses a source-oriented reuse pass over normalized structural expressions.

It now supports three useful behaviors:

### 1. Repeated chain reuse

Example:

```python
shared = chain('Shared 1', 'Shared 2', 'Shared 3')
```

### 2. Repeated subtree reuse

Example:

```python
choice = node(
    'Choice',
    node('X'),
    node('Y')
)
```

used in multiple places.

### 3. Shared terminal reuse across aliased parents

Example from current behavior:

```python
alnd = node('ALND [II, A]')
rt = node('RT (axilla) [II, B]')
```

when those terminals are reused across multiple distinct larger contexts.

This was added after discovering that a pure “maximal parent only” policy over-blocked useful shared terminal aliases in `ebc-aln`.

---

## Current naming behavior

Variable names are now intentionally shorter.

Default naming policy:
- start with the first word only
- add more words only if needed to disambiguate

Examples:
- `ALND [II, A]` -> `alnd`
- `RT (axilla) [II, B]` -> `rt`
- `Shared 1 / Shared 2 / Shared 3` -> `shared`
- collisions expand incrementally, e.g.:
  - `rt`
  - `rt_axilla`
  - `rt_basis`

This reduces output verbosity, but it also increases the importance of having a single, testable naming policy.

