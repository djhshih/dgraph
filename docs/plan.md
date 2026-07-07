# Plan: improve `walk()` output

See also: `constraints.md`.

This plan focuses only on making `walk()` more useful while keeping the code and graph simple.

## Current problem

`walk()` currently returns:

- matching completed paths
- a flat list of required attrs collected from children at the end of those paths

This is too weak for partial input.

Problems with the current output:

- it does not clearly show where traversal stopped
- it does not show which next branches were considered
- it mixes together different kinds of "required" values
- it does not help a caller decide what question to ask next
- it is hard to use when input is incomplete

## Goal

Keep traversal simple, but return enough information that a caller can:

- see the completed matching paths
- see the current frontier
- see what values would let traversal continue
- see likely next questions
- see possible action leaves already reached

## Proposed shape

Keep the existing `walk()` behavior available, but move toward returning a small structured result.

Suggested result shape:

```python
{
    "completed_paths": list[list[str]],
    "frontier": list[{
        "path": list[str],
        "node": str,
        "next": list[str],
        "missing": list[str],
    }],
    "next_values": list[str],
    "actions": list[list[str]],
}
```

Notes:

- `completed_paths`: all fully traversed matching paths
- `frontier`: places where traversal stopped but children exist
- `frontier[i]["path"]`: the matched path up to the stopping point
- `frontier[i]["node"]`: the stopping node label
- `frontier[i]["next"]`: labels of immediate child branches from that node
- `frontier[i]["missing"]`: values inferred from child conditions that would allow progress
- `next_values`: deduplicated union of all frontier `missing` values
- `actions`: completed paths that end in leaves; this is mainly a convenience alias for callers

## Implementation steps

### 1. Add a new walker result without breaking old callers

Add a new function first, for example:

- `walk_details(node, x)`

Keep `walk(node, x)` working as it does now until the new result shape is proven useful.

### 2. Track frontier explicitly during traversal

When traversal reaches a node where:

- the node itself matches
- none of its children match
- and it still has children

record a frontier item for that node.

Each frontier item should include:

- the matched path so far
- the node label
- immediate child labels
- inferred missing values from those child conditions

### 3. Keep missing values simple

Only report values already exposed by the existing condition helpers through `attrs`.

Do not add a new inference system.

For now, this means:

- for tag-based branches, report the tag values already carried in `attrs`
- for scalar attrs, report the attr name if that is all we know

The rule should be simple enough that a reader can predict the output by reading the graph.

### 4. Add a simple "next question" helper

Add a tiny helper built on top of `walk_details()`, for example:

- `suggest_next_values(result)`

Behavior:

- take `result["next_values"]`
- deduplicate while preserving order
- return the smallest useful list of candidate next values to ask about

This should stay simple and deterministic.

### 5. Add a simple action helper

Add a helper, for example:

- `extract_actions(result)`

Behavior:

- return completed paths ending in leaves
- optionally also return the final leaf labels only

This avoids forcing every caller to re-derive actions from completed paths.

## Concrete examples to support

### Example 1: partial HER2 branch

If the graph is:

- `EBC`
  - `HER2+`
    - `cT1 N0`
    - `>=cT2 or cN+`

and input is:

- `HER2+`

then the result should make it obvious that:

- path `EBC -> HER2+` is currently reached
- traversal stopped there
- the next branch labels are `cT1 N0` and `>=cT2 or cN+`
- the missing values include the values inferred from those branch conditions

### Example 2: complete leaf path

If input reaches a leaf, the result should include that path in:

- `completed_paths`
- `actions`

and frontier should not include that leaf.

### Example 3: multiple matching frontiers

If input matches more than one branch family, the result should include all current frontiers, not only one flattened required-value list.

## Tests to add

Add focused tests for `walk_details()`:

1. returns completed path for a full match
2. returns one frontier item when parent matches but children do not
3. returns multiple frontier items when multiple branches remain open
4. deduplicates `next_values` in stable order
5. keeps child branch labels in graph order
6. treats leaves as completed paths, not frontier items
7. handles cycles the same way `walk()` does now
8. matches current `walk()` path behavior for completed paths

## Non-goals

- no new DOT metadata system
- no recommendation engine
- no complex schema redesign
- no large refactor of graph construction helpers
- no attempt to fully formalize free-text labels

## Success criteria

This work is successful if:

- `walk_details()` is easy to explain in a few sentences
- a reader can predict its output from the graph structure
- tests show useful behavior with incomplete input
- callers can directly use the output to decide what to ask next
- the code stays small and readable
