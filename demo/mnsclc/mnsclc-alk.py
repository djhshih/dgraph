# Stage IV mNSCLC with ALK translocation
# Figure 3, Planchard et al., 2022, https://doi.org/10.1016/j.annonc.2022.12.009

from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.graph import Data, walk
from dgraph.schema import infer_schema, validate_data


ROOT = Path(__file__).resolve().parents[2]
graph = load_dg(ROOT / "data/mnsclc/dg/mnsclc_alk.dg")

schema = infer_schema(graph)
print(f"schema: {schema} \n")

examples = [
    Data(set()),
    Data(("Oligoprogression",)),
    Data(("Systemic_progression",)),
    Data(("Systemic_progression", "after_crizotinib")),
    Data(("Systemic_progression", "after_ALK_TKI_not_crizotinib")),
]

for x in examples:
    result = validate_data(schema, x)
    if result:
        print(f"validation error: {result}")
        continue

    print(f"\nWalking the graph with data: {x.tags}: ")

    paths, required = walk(graph, x)
    print(f"paths: {len(paths)}")
    for index, p in enumerate(paths):
        print(f"  {index}: {p}")
    print(f"\nrequired: {required}")
