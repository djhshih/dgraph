from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.graph import walk
from dgraph.patient_data import build_patient, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[2]
DOI = "https://doi.org/10.1016/j.annonc.2022.05.009"

DEMOS = [
    {
        "title": "Molecular classification of EC",
        "citation": f"Figure 1, {DOI}",
        "graph": ROOT / "data/emc/dg/molecular_classification.dg",
        "patients": ROOT / "demo/patients/emc/molecular_classification.json",
    },
    {
        "title": "Stage I EC: surgery",
        "citation": f"Figure 2, {DOI}",
        "graph": ROOT / "data/emc/dg/stage_1_surgery.dg",
        "patients": ROOT / "demo/patients/emc/stage_1_surgery.json",
    },
    {
        "title": "Adjuvant therapy for low- and intermediate-risk EC",
        "citation": f"Figure 3, {DOI}",
        "graph": ROOT / "data/emc/dg/adjuvant_low_intermediate.dg",
        "patients": ROOT / "demo/patients/emc/adjuvant_low_intermediate.json",
    },
    {
        "title": "Adjuvant therapy for high-intermediate and high-risk EC",
        "citation": f"Figure 4, {DOI}",
        "graph": ROOT / "data/emc/dg/adjuvant_intermediate_high.dg",
        "patients": ROOT / "demo/patients/emc/adjuvant_intermediate_high.json",
    },
    {
        "title": "Locoregional recurrent EC",
        "citation": f"Figure 5, {DOI}",
        "graph": ROOT / "data/emc/dg/locoregional_recurrence.dg",
        "patients": ROOT / "demo/patients/emc/locoregional_recurrence.json",
    },
    {
        "title": "Recurrent / metastatic EC",
        "citation": f"Figure 6, {DOI}",
        "graph": ROOT / "data/emc/dg/metastatic_curated.dg",
        "patients": ROOT / "demo/patients/emc/metastatic.json",
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
