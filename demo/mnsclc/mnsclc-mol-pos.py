# Stage IV mNSCLC molecular tests positive
# Figure 1, Planchard et al., 2022, https://doi.org/10.1016/j.annonc.2022.12.009

from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.graph import Data, walk
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[2]
graph = load_dg(ROOT / "data/mnsclc/dg/mnsclc_mol_pos.dg")

schema = infer_schema(graph)
print(f"schema: {schema} \n")

examples = [
    Data(set()),

    Data(("EGFR_mutation",)),
    Data(("EGFR_mutation", "Oligoprogression")),

    Data(("ALK_translocation",)),
    Data(("ALK_translocation", "Systemic_progression")),
    
    Data(("ROS1_translocation",)),
    Data(("BRAF_V600_mutation",)),
    Data(("RET_translocation",)),
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
