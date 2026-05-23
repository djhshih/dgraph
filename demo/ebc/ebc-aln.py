# Management of ALN involvement in early breast cancer
# Figure 3, Loibl et al., 2024, https://doi.org/10.1016/j.annonc.2023.11.016

# TODO we need a stopping condition and an action list!

from dataclasses import dataclass

import dgraph.condition as dc
from dgraph.graph import Data as GraphData, branch, case, match, node, walk
from dgraph.schema import infer_schema, validate_data


@dataclass
class Data(GraphData):
    positive_nodes: int


rt_ba = node("RT (basis axilla) [II, B]")
rt_a = node("RT (axilla) [II, B]")
alnd_local = node("ALND [II, A]")
alnd_regional = node("ALND (or RT) of regional LNs [II, B]")

sln_neg = branch(
    "SLN-",
    dc.has("SLN-"),
    node("No further locoregional treatment"),
)

bottom_branches = (
    branch("ACOSOG-Z0011 criteria met", dc.has("ACOSOG-Z0011+"), rt_ba),
    branch("AMAROS critiera met", dc.has("AMAROS+"), rt_a, alnd_local),
    branch(
        "ACOSOG-Z0011 criteria not met or >2 positive LNs",
        dc.all_of(dc.has("ACOSOG-Z0011-"), dc.gt("positive_nodes", 2)),
        alnd_local,
    ),
)

slnb = node(
    "SLNB [I, A]",
    sln_neg,
    branch("SLN+", dc.has("SLN+"), bottom_branches),
)

biopsy = node(
    "Biopsy",
    match(
        "tags",
        case("pNX", slnb),
        case("pN+", bottom_branches),
    ),
)

surgery_indicated = branch(
    "primary surgery indicated",
    dc.has("primary_surgery"),
    match(
        "tags",
        case(("N0", "cN0", "iN0"), node("SLNB [I, A]", slnb.children), label="cN0/iN0"),
        case(("N+", "cN+", "iN+"), biopsy, label="cN+/iN+"),
    ),
)

neoadjuvant_therapy = node(
    "Follow Figures 4-7 for neoadjuvant therapy",
    branch(
        "ycN0/ypN0 after neoadjuvant ChT",
        dc.has_any("ycN0", "ypN0"),
        branch(
            "SLN- or TAD-",
            dc.has_any("SLN-", "TAD-"),
            node("Consider RT if pN+ at primary diagnosis [II, B]"),
        ),
        branch(
            "SLN+ or TAD+",
            dc.has_any("SLN+", "TAD+"),
            alnd_regional,
        ),
    ),
    branch(
        "ycN+/ypN+ after neoadjuvant ChT",
        dc.has_any("ycN+", "ypN+"),
        alnd_regional,
    ),
)

neoadjuvant_indicated = branch(
    "PST indicated",
    dc.has("neoadjuvant"),
    branch("cN0/pN0 at primary diagnosis", dc.has_any("cN0", "pN0"), neoadjuvant_therapy),
    branch("cN+/pN+ at primary diagnosis", dc.has_any("cN+", "pN+"), neoadjuvant_therapy),
)

graph = node(
    "EBC-ALN",
    surgery_indicated,
    neoadjuvant_indicated,
)

schema = infer_schema(graph)
print(schema)

examples = [
    Data(("primary_surgery", "iN+"), positive_nodes=3),
    Data(("primary_surgery", "cN+", "pN+", "ACOSOG-Z0011+"), positive_nodes=1),
    Data(("primary_surgery", "cN+", "pN+", "AMAROS+"), positive_nodes=1),
    Data(("neoadjuvant", "cN0"), positive_nodes=0),
]

for x in examples:
    print(validate_data(schema, x))
    print(walk(graph, x))
