from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.graph import walk
from dgraph.patient_data import build_patient, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[2]
DOI = "https://doi.org/10.1016/j.annonc.2023.07.011"

DEMOS = [
    {
        "title": "Early EOC (FIGO stage I-II)",
        "citation": f"Figure 1, {DOI}",
        "graph": ROOT / "data/eoc/dg/eoc_early.dg",
        "patients": ROOT / "demo/patients/eoc/eoc_early.json",
    },
    {
        "title": "Newly diagnosed advanced EOC (FIGO stage III-IV)",
        "citation": f"Figure 2, {DOI}",
        "graph": ROOT / "data/eoc/dg/eoc_advanced.dg",
        "patients": ROOT / "demo/patients/eoc/eoc_advanced.json",
    },
    {
        "title": "Recurrent EOC",
        "citation": f"Figure 3, {DOI}",
        "graph": ROOT / "data/eoc/dg/eoc_recurrent.dg",
        "patients": ROOT / "demo/patients/eoc/eoc_recurrent.json",
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
