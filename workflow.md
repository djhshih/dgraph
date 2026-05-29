# Workflow

Each subdir in `data` contains the decision tree for one set of guidelines.

1. Download image from website to `data/*/img`.
2. Generate dot files
    - Extract graph from image and write in DOT format (external service) to
   `data/*/dot`
    - Generate pdf from dot files and ensure correctness
    - Remove unnecessary words and characters from the labels
      (e.g. footnote letters, "All HR+" -> "HR+")
    - Add or preserve `\n` for sets of conditions, but remove `\n` that exists for formatting purposes
    - Combine phrases with `_` (e.g. "stage I" -> "stage_I",
      "cN0 at primary diagnosis" -> "cN0_at_primary_diagnosis").
      This is to support implicit "and" operations, e.g. "cT1 cN0"
    - Convert set union "and" to logical "or", e.g.
      "premenopausal patients and postmenopasual patients" -> "premenopasual or
      postmenopausal"
    - Use brackets to ensure that "and" and "or" operator priorities are correct by examining
      competing branches. Natural language is quite ambiguity in terms of operator precedence.
    - These steps may be facilitated with an LLM, but results must be curated
    - Commit the dot file
4. Generate dg files
    - Run `bin/dot2dg.py` to generate dg code from dot files, writing to
      `data/*/dg`
    - If dg file is mostly good, commit it as a draft.
    - Edit the dg code to ensure that conditions are correct.
    - Commit the final dg file.
4. Prepare patient data in `data/*/patient`.
5. In Python, run `dgraph.graph.walk(graph, data)` to walk through a decision 
   graph with patient data to return all viable paths and attributes required to continue.

