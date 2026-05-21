# Management of ALN involvement in early breast cancer
# Figure 3, Loibl et al., 2024, https://doi.org/10.1016/j.annonc.2023.11.016

# TODO we need a stopping condition and an action list!

# TODO distinguish between different node status: c vs. i vs. p

# NOTE  use n_status == "pNX" rather than n_status != "pN+"
#       allows the walk to stop because condition of neither branch is met


import os, sys

from dataclasses import dataclass

sys.path.append(os.path.abspath('..'))
import dgraph.condition as dc
import dgraph.graph as dg
from dgraph.graph import branch, case, match, node


@dataclass
class Data(dg.Data):
    neoadjuvant: bool = None
    # c: clinical (palpation); i: imaging; p: pathological
    n_status: str = None
    sln_positive: bool = None
    acosog_z0011: bool = None
    amaros: bool = None
    positive_nodes: int = None
    # y: after neoadjuvant
    n_status_residual: str = None    # ycN0, ypN0, ycN+, ypN+
    tad_positive: bool = None


rt_ba = node("RT (basis axilla) [II, B]")
rt_a = node("RT (axilla) [II, B]")
alnd_local = node("ALND [II, A]")
alnd_regional = node("ALND (or RT) of regional LNs [II, B]")

sln_neg = branch(
    "SLN-",
    dc.is_false("sln_positive"),
    node("No further locoregional treatment"),
)

bottom_branches = [
    branch("ACOSOG-Z0011 criteria met", dc.is_true("acosog_z0011"), rt_ba),
    branch("AMAROS critiera met", dc.is_true("amaros"), rt_a, alnd_local),
    branch(
        "ACOSOG-Z0011 criteria not met or >2 positive LNs",
        dc.all_of(dc.is_false("acosog_z0011"), dc.gt("positive_nodes", 2)),
        alnd_local,
    ),
]

slnb = node(
    "SLNB [I, A]",
    sln_neg,
    branch("SLN+", dc.is_true("sln_positive"), bottom_branches),
)

biopsy = node(
    "Biopsy",
    match(
        "n_status",
        case("pNX", slnb),
        case("pN+", bottom_branches),
    ),
)

surgery_indicated = branch(
    "primary surgery indicated",
    dc.is_false("neoadjuvant"),
    match(
        "n_status",
        case(("cN0", "iN0"), node("SLNB [I, A]", slnb.children), label="cN0/iN0"),
        case(("cN+", "iN+"), biopsy, label="cN+/iN+"),
    ),
)

neoadjuvant_therapy = node(
    "Follow Figures 4-7 for neoadjuvant therapy",
    branch(
        "ycN0/ypN0 after neoadjuvant ChT",
        dc.is_in("n_status_residual", ("ycN0", "ypN0")),
        branch(
            "SLN- or TAD-",
            dc.any_of(dc.is_false("sln_positive"), dc.is_false("tad_positive")),
            node("Consider RT if pN+ at primary diagnosis [II, B]"),
        ),
        branch(
            "SLN+ or TAD+",
            dc.any_of(dc.is_true("sln_positive"), dc.is_true("tad_positive")),
            alnd_regional,
        ),
    ),
    branch(
        "ycN+/ypN+ after neoadjuvant ChT",
        dc.is_in("n_status_residual", ("ycN+", "ypN+")),
        alnd_regional,
    ),
)

neoadjuvant_indicated = branch(
    "PST indicated",
    dc.is_true("neoadjuvant"),
    branch("cN0/pN0 at primary diagnosis", dc.is_in("n_status", ("cN0", "pN0")), neoadjuvant_therapy),
    branch("cN+/pN+ at primary diagnosis", dc.is_in("n_status", ("cN+", "pN+")), neoadjuvant_therapy),
)

graph = node(
    "EBC-ALN",
    surgery_indicated,
    neoadjuvant_indicated,
)

schema = dg.infer_schema(graph)
print(schema)

examples = [
    Data(neoadjuvant=False, n_status="iN+", positive_nodes=3),
    Data(neoadjuvant=False, n_status="cN+", positive_nodes=1),
    Data(neoadjuvant=False, n_status="cN+", positive_nodes=1),
    Data(neoadjuvant=True, n_status="cN0"),
]

for x in examples:
    print(dg.validate_data(schema, x))
    print(dg.walk(graph, x))
