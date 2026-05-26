# Plan to improve `dgraph/` and `demo/`

## 1. Immediate bug fixes

1. **Fix the DOT parser so it handles common single-line DOT input**
   - `dgraph/dot/parse.py` currently parses line-by-line and ignores a line starting with `digraph ...`, which causes valid one-line DOT graphs such as `digraph G { a [label="A"]; a -> b; }` to be treated as empty.
   - Replace the current line-oriented parser with a statement-oriented tokenizer/parser that splits on semicolons/braces while preserving quoted strings and escaped content.
   - Support both one-line and multi-line DOT, and add regression tests for both forms.

2. **Fix inconsistent return type / docstring in `walk()`**
   - `dgraph/graph.py:127` says it returns a list of paths, but actually returns `(paths, required)`.
   - Update type annotations and docstring to match reality, or better, introduce a structured result type such as `WalkResult(paths, required, frontier, matched_conditions)`.

3. **Fix `Data.tags` typing and data model consistency**
   - `Data.tags` is typed as bare `set`, but demos pass tuples.
   - Make `tags` type explicit (`Collection[str]` or `frozenset[str]`) and normalize input in `Data.__post_init__`.
   - Ensure all condition helpers operate safely on normalized tag collections.

4. **Fix schema inference and validation mismatch for tagless linear graphs**
   - `demo/ebc/ebc-dx.py` produces `{}` schema, but validating `Data(("HR+",))` reports `Unknown tag 'HR+'` because validation rejects any tag not in schema.
   - Intended behavior:
     - allow arbitrary tags when the graph never references tags,
   - Update `validate_data()` accordingly and add tests.

5. **Fix required-attributes reporting in graph walking**
   - `walk()` returns raw `condition.attrs`, which may contain tuples of possible values for tag conditions like `('T1', 'cT1')` rather than a normalized “missing evidence” structure.
   - Replace this with explicit frontier questions, e.g. “need one of {T1, cT1}” or “need `positive_nodes`”.
   - This is essential for agent-driven next-step recommendations.

6. **Document demo.sh in README**


## 2. DOT-to-DSL accuracy improvements

5. **Improve source generation fidelity and readability**
   - `ir_to_source()` should preserve:
     - deterministic order
     - reusable subtrees/aliases
     - metadata comments where conversion was heuristic
   - Emit source that is idiomatic and editable by humans, not just structurally equivalent.

6. **Add round-trip and semantic equivalence tests**
   - Test: DOT -> IR -> source -> imported graph -> walk equivalence.
   - Test multi-root, shared-node, cyclic, and repeated-subtree cases.
   - Test clinical label cases that currently stress condition inference.

## 3. Graph walking improvements for AI-agent decision support

1. **Redesign walking around partial evidence**
   - Current `walk()` only returns fully traversed matching paths plus a crude list of required attrs at path ends.
   - Add a first-class frontier model describing:
     - current reachable nodes
     - satisfied conditions
     - blocked branches
     - missing evidence to advance
     - conflicting evidence
   - This makes the engine usable for iterative agent questioning.

2. **Return structured recommendation objects instead of raw tuples**
   - Proposed return structure:
     - `completed_paths`
     - `frontier_nodes`
     - `missing_inputs`
     - `candidate_next_questions`
     - `recommended_actions`
     - `explanations`
   - This enables an AI agent to ask the most informative next question and justify recommendations.

5. **Add conflict detection in patient data**
   - Clinical inputs can be contradictory (`HR+` and `HR-`, `cN0` and `cN+`).
   - Introduce validation rules and conflict diagnostics before walking.
   - `walk()` / evaluation should surface contradictions and suppress invalid branches cleanly.

## 4. Maintainability improvements

4. **Tighten typing throughout**
   - Use precise types for `Data`, conditions, walker results, schema, and DOT IR.
   - Replace ambiguous `Any` where practical.
   - Introduce protocols or dataclasses for evaluator outputs.

5. **Reduce magic via explicit metadata models**
   - Current schema inference relies on function closures and overloaded `attrs` metadata.
   - Replace this with explicit condition metadata fields so schema inference, validation, and recommendation logic are robust and inspectable.

6. **Clarify module boundaries**
   - Suggested layering:
     - `condition.py`: declarative predicates + introspectable metadata
     - `graph.py`: graph structures and constructors
     - `engine.py` or `walk.py`: traversal/evaluation/recommendation
     - `schema.py`: schema + validation
     - `dot/*`: parsing/import/export/diagnostics
   - This will make future extensions easier.

8. **Document expected graph authoring patterns**
   - Add docs for:
     - when to use `chain`, `node`, `branch`, `match`
     - how to model action vs decision nodes
     - how to express conditions safely
     - how DOT conversion interprets labels and attributes

## 5. Demo improvements

2. **Add richer patient examples for recommendation workflows**
   - Include examples with incomplete data, conflicting data, and progressive disclosure.
   - Demonstrate “what question should the agent ask next?”

3. **Mark action nodes and stopping conditions explicitly in demos**
   - `demo/ebc/ebc-aln.py` already notes the need for a stopping condition and action list.
   - Add these as part of the graph model instead of leaving them as comments.

## 7. Highest-priority concrete issues found from this review

1. **Confirmed bug:** one-line DOT graphs parse as empty.
2. **Confirmed issue:** demos require `PYTHONPATH=.` to run directly.
3. **Confirmed issue:** `walk()` API/documentation mismatch and weak required-input reporting.
4. **Confirmed issue:** schema validation rejects arbitrary tags even when the graph schema is empty.
5. **Design issue:** DOT conversion accuracy depends too heavily on label heuristics.
6. **Design issue:** graph walking is not yet structured enough for AI-agent next-step recommendation workflows.

