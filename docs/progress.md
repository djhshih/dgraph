## To do
- download images from all guidelines in guidelines.md
- ensure correctness of
```
infer_schema()
validate_data()
```
- regular expression on attribute tags?
- condition evaluation on attribute tags?
    - >=cT2, cT1c-4
- tag expansion: graph condition or patient data?
    - graph condition
        - >=cT2 -> (cT2, cT3, cT4)
        - cT1c-4 -> (cT1c, cT2, cT3, cT4)
        - HR+ -> ER+ or HR+
    - patient data
        - ER+ -> (ER+, HR+)
        - PR+ -> (PR+, HR+)
        - cT3 -> (>=cT2, cT1c-4)
    - common abbreviations?
        - (BRCA1/2 -> BRCA1/BRCA2)

## To do (low priority)
- image to dot (using external service)

## Completed
- graph construction
- graph walking
- dot to source dg (dgraph.dot.compile)
- dot to runtime graph (dgraph.dot.interpret)
- dot IR optimization to reduce duplicate nodes

