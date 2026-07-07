# Constraints

This project must stay simple.

## Core constraints

- The graph should be easy to read in code.
- The graph should be easy to inspect at runtime.
- A human should be able to look at the graph-building code and the resulting graph and understand both without extra tooling.
- Prefer a small number of obvious concepts over a rich framework.
- Do not introduce designs that require hidden semantics or complex internal machinery.

## Input-data constraints

- The source data is sparse and messy.
- The input data does not carry rich formal metadata.
- DOT input is mostly labels and edges.
- Clinical meaning is often encoded only in free-text labels.
- The system cannot depend on upstream structured metadata that does not exist.

## Design constraints

- Keep `Node`, `branch`, `chain`, `match`, and `walk` easy to understand.
- Avoid adding layers that make the graph harder to reason about.
- Avoid over-engineering around schemas, diagnostics, recommendation frameworks, or complex intermediate models.
- Any improvement to `walk()` should be understandable from the function signature and returned value.
- Prefer returning plain Python data structures or very small dataclasses.

## Practical implications

- Improvements should focus on making `walk()` more useful with partial input.
- Improvements should focus on concrete outputs that help a caller decide what to ask for next.
- Improvements should not assume the graph can be made fully explicit or fully formal.
- Improvements should not depend on magical metadata in DOT files or patient input.
- When in doubt, choose the simpler representation.
