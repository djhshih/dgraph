# Stage IV mNSCLC with ROS1 translocation
# Figure 4, Planchard et al., 2023, https://doi.org/10.1016/j.annonc.2022.12.009

from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.graph import Data, walk
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[2]
graph = load_dg(ROOT / "data/mnsclc/dg/mnsclc_ros1.dg")

schema = infer_schema(graph)
print(f'schema: {schema} \n')

examples = [
    Data(set()),
    Data(("Oligoprogression",)),
    Data(("Systemic_progression",)),
    Data(("Oligoprogression", "no_ROS1_TKI_received_in_first_line")),
    Data(("Systemic_progression", "ROS1_TKI_received_in_first_line")),
]

for x in examples:
    result = validate_data(schema, x)
    if result:
        print(f'validation error: {result}')
        continue

    print(f'\n Walking the graph with data: {x}: ')

    paths, required = walk(graph,x)
    print(f'paths: {len(paths)}')
    for (index, p) in enumerate(paths):
        print(f"  {index}: {p}")
    print(f'\n required: {required}')