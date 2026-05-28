# Strategies to facilitate graph construction by an LLM

## Add validation before execution
An LLM-generated graph should be validated before calling `walk()`.

Suggested checks:
- missing referenced node IDs
- duplicate IDs
- unreachable nodes
- cycles
- multiple roots
- suspicious labels used as conditions
- empty labels
- repeated children on the same parent

Recommended API:
- `validate_graph_spec(spec) -> list[str]`
- `analyze_graph(root) -> report`

## Add normalization helpers
LLMs often produce label variations:
- `HER2+`
- `HER2 +`
- `her2+`
- `Primary surgery ± RT`
- `Primary surgery +/- RT`

Helpful utilities:
- label normalization
- synonym tables
- canonical token mapping

Caution:
- normalization should be optional and explicit
- avoid silently changing clinical semantics

## Add examples optimized for prompting
Provide small canonical examples:
- simple chain
- binary branch
- multi-branch decision
- reusable subgraph
- cyclic graph example and expected behavior

For each example include:
- Python construction
- DOT form
- JSON/spec form
- expected `walk()` output

This greatly improves LLM reliability.

