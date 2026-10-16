# Workflow

Each subdir in `data` contains the decision tree for one set of guidelines.

How to check and fix DOT vs generated/curated DG: [`docs/dot_dg_review.md`](dot_dg_review.md). DOT extraction prompt: `data/prompt.txt` (leave the prompt as-is).

1. Download the figure to `data/<tumour>/img`.
2. Write DOT under `data/<tumour>/dot` (external extract, then review). Generate a PDF and confirm it matches the figure.
3. Compile DG with `bin/dot2dg.py` (or `make` in `data/<tumour>/dg`). Add `*_curated.dg` only when the compiler’s conditions are wrong.
4. Dummy patient fixtures in `demo/patients/<tumour>/` (demos and tests only).
5. `dgraph.graph.walk(graph, data)` returns matching paths and attributes needed to continue.
6. Add new tags-medical_context pair to glossary.md

