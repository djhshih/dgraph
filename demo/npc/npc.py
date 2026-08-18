from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.graph import walk
from dgraph.patient_data import build_patient, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[2]
DOI_2022 = "https://doi.org/10.1016/j.annonc.2022.11.011"
DOI_2021 = "https://doi.org/10.1016/j.annonc.2020.12.007"

DEMOS = [
    {
        "title": "Locoregional NPC",
        "citation": f"Figure 1, {DOI_2022}",
        "graph": ROOT / "data/npc/dg/locoregional_curated.dg",
        "patients": ROOT / "demo/patients/npc/locoregional.json",
    },
    {
        "title": "Recurrent or metastatic NPC",
        "citation": f"Figure 2, {DOI_2022}",
        "graph": ROOT / "data/npc/dg/recurrent_metastatic.dg",
        "patients": ROOT / "demo/patients/npc/recurrent_metastatic.json",
    },
    {
        "title": "Follow-up of NPC",
        "citation": f"Figure 3, {DOI_2021}",
        "graph": ROOT / "data/npc/dg/follow_up_curated.dg",
        "patients": ROOT / "demo/patients/npc/follow_up.json",
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
