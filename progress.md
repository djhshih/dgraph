## To do
- condition inference: logical syntax
    - only "and", "or", "/" are supported
- condition inference: logical statement expansion, e.g.
    - >= cT2 -> (cT2, cT3, cT4)
    - cT1c-4 -> (cT1c, cT2, cT3, cT4)
- patient data extraction and expansion, e.g.
    - ER+ -> (ER+, HR+)
    - PR+ -> (PR+, HR+)
- download images from all guidelines in guidelines.md
- dot graph optimization to reduce duplicate nodes (e.g. data/ebc/ebc.dot)

## Improve
- dot to graph (source)
- dot to graph (runtime object)

## To do (low priority)
- image to dot (using external service)

## Completed
- graph construction
- graph walking

