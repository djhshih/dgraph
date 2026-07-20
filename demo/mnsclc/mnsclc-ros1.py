# Stage IV mNSCLC with ROS1 translocation
# Figure 4, Planchard et al., 2023, https://doi.org/10.1016/j.annonc.2022.12.009

from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.graph import walk
from dgraph.patient_data import build_patient, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[2]
graph = load_dg(ROOT / "data/mnsclc/dg/mnsclc_ros1.dg")

schema = infer_schema(graph)
print(f"schema: {schema} \n")

cases = load_patient_cases(ROOT / "data/mnsclc/patient/mnsclc-ros1.json")

for case in cases:
    x = build_patient(schema, case)
    result = validate_data(schema, x)
    if result:
        print(f"validation error for {case.get('id')}: {result}")
        continue

    print(f"\nWalking the graph for {case.get('id')}:")

    paths, required = walk(graph, x)
    print(f"paths: {len(paths)}")
    for index, p in enumerate(paths):
        print(f"  {index}: {p}")
    print(f"\nrequired: {required}")
