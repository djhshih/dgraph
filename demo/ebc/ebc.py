# Early breast cancer treatment overview
# Figure 2, Loibl et al., 2024, https://doi.org/10.1016/j.annonc.2023.11.016

import dgraph.condition as dc
from dgraph.graph import Data, branch, chain, node, walk
from dgraph.schema import infer_schema, validate_data


surgery_systemic = chain("Primary surgery +/- RT", "Systemic treatment")
neoadjuvant_surgery_systemic = chain("Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment")

graph = node(
    "EBC",
    branch("HR+", dc.has("HR+"), node("ET [I, A]")),
    branch(
        "Premenopausal patients receiving OFS and postmenopausal patients",
        dc.any_of(
            dc.has("postmenopausal"),
            dc.all_of(dc.has("premenopausal"), dc.has("receiving_ofs")),
        ),
        node("Adjuvant bisphosphonates [I, A]"),
    ),
    branch(
        "HR+/HER2-",
        dc.has_all("HR+", "HER2-"),
        neoadjuvant_surgery_systemic,
    ),
    branch(
        "HER2+",
        dc.has("HER2+"),
        branch(
            "cT1 N0",
            dc.all_of(dc.has_any("T1", "cT1"), dc.has_any("N0", "cN0")),
            surgery_systemic,
        ),
        branch(
            ">=cT2 or cN+",
            dc.has_any("T2", "T3", "T4", "cT2", "cT3", "cT4", "N+", "cN+"),
            neoadjuvant_surgery_systemic,
        ),
    ),
    branch(
        "TNBC",
        dc.has_all("HR-", "HER2-"),
        branch(
            "cT1a or cT1b N0",
            dc.all_of(dc.has_any("T1a", "T1b", "cT1a", "cT1b"), dc.has_any("N0", "cN0")),
            surgery_systemic,
        ),
        branch(
            "cT1c-4 or N+",
            dc.any_of(dc.has_any("T1c", "T2", "T3", "T4", "cT1c", "cT2", "cT3", "cT4"), dc.has_any("N+", "cN+")),
            neoadjuvant_surgery_systemic,
        ),
    ),
)

schema = infer_schema(graph)
print(schema)

examples = [
    Data(("HR+",)),
    Data(("HER2+", "HR-")),
    Data(("HER2+", "HR-", "T1", "N0")),
    Data(("HER2-", "HR-", "T1a", "N0")),
    Data(("HER2-", "HR-", "T1a", "N+")),
    Data(("HER2+", "HR-", "T1", "N+")),
    Data(("HER2-", "HR+", "T1", "N0")),
]

for x in examples:
    print(validate_data(schema, x))
    print(walk(graph, x))
