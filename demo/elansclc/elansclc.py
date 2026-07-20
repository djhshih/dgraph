from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.graph import walk
from dgraph.patient_data import build_patient, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[2]

DEMOS = [
    {
        "title": "Stage I NSCLC (locoregional staging)",
        "citation": "Figure 1, https://doi.org/10.1016/j.annonc.2025.08.003",
        "graph": ROOT / "data/elansclc/dg/locoregional_staging_curated.dg",
        "patients": ROOT / "data/elansclc/patient/locoregional_staging.json",
    },
    {
        "title": "Resectable stage II-III NSCLC",
        "citation": "Figure 2, https://doi.org/10.1016/j.annonc.2025.08.003",
        "graph": ROOT / "data/elansclc/dg/resectable.dg",
        "patients": ROOT / "data/elansclc/patient/resectable.json",
    },
]


def run_demo(title: str, citation: str, graph_path: Path, patient_path: Path) -> None:
    print(f"# {title}")
    print(f"# {citation}\n")

    graph = load_dg(graph_path)
    schema = infer_schema(graph)
    cases = load_patient_cases(patient_path)

    print(f"schema: {schema}\n")

    for case in cases:
        x = build_patient(schema, case)
        result = validate_data(schema, x)
        if result:
            print(f"validation error for {case.get('id')}: {result}")
            continue

        print(f"\nWalking the graph for {case.get('id')}:")
        paths, required = walk(graph, x)
        print(f"paths: {len(paths)}")
        for index, path in enumerate(paths):
            print(f"  {index}: {path}")
        print(f"\nrequired: {required}")

    print("\n" + "=" * 80 + "\n")


for demo in DEMOS:
    run_demo(
        demo["title"],
        demo["citation"],
        demo["graph"],
        demo["patients"],
    )
