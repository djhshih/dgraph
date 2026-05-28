## To do
- ensure correctness of
```
infer_schema()
validate_data()
```
- download images from all guidelines in guidelines.md
- regular expression on attribute tags?
- common synonyms (BRCA1/2 -> BRCA1/BRCA2)
- condition inference from dot files, including tag expansion, e.g.
    - >=cT2 -> (cT2, cT3, cT4)
    - cT1c-4 -> (cT1c, cT2, cT3, cT4)
- condition inference: logical syntax
    - only "and", "or", "/" are supported
- tag extraction from patient data, including tag expansion, e.g.
    - ER+ -> (ER+, HR+)
    - PR+ -> (PR+, HR+)

## To do (low priority)
- image to dot (using external service)

## Completed
- graph construction
- graph walking
- dot to source dg (dgraph.dot.source)
- dot to runtime graph (dgraph.dot.build)
- dot graph optimization to reduce duplicate nodes

