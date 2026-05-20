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
from dgraph.graph import Node

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

rt_ba = Node("RT (basis axilla) [II, B]")
rt_a = Node("RT (axilla) [II, B]")
alnd = Node("ALND [II, A]")

sln_neg = Node("SLN-",
    condition = dc.is_false("sln_positive"),
    children = [
        Node("No further locoregional treatment")
    ],
)

bottom_branches = [
    Node("ACOSOG-Z0011 criteria met",
        condition = dc.is_true("acosog_z0011"),
        children = [ rt_ba ]
    ),
    Node("AMAROS critiera met",
        condition = dc.is_true("amaros"),
        children = [ rt_a, alnd ]
    ),
    Node("ACOSOG-Z0011 criteria not met or >2 positive LNs",
        condition = dc.all_of(dc.is_false("acosog_z0011"), dc.gt("positive_nodes", 2)),
        children = [ alnd ]
    ),
]

sln_pos = Node("SLN+",
    condition = dc.is_true("sln_positive"),
    children = bottom_branches,
)

slnb = Node("SLNB [I, A]",
    children = [sln_neg, sln_pos]
)

biopsy = Node("Biopsy",
    children = [
        Node("pNX",
            condition = dc.equals("n_status", "pNX"),
            children = [ slnb ]
        ),
        Node("pN+",
            condition = dc.equals("n_status", "pN+"),
            children = bottom_branches
        )
    ]
)

surgery_indicated = Node("primary surgery indicated",
    condition = dc.is_false("neoadjuvant"),
    children = [
        Node("cN0/iN0",
            condition = dc.contains("n_status", ("cN0", "iN0")),
            children = [ slnb ]
        ),
        Node("cN+/iN+",
            condition = dc.contains("n_status", ("cN+", "iN+")),
            children = [ biopsy ]
        ),
    ]
)

alnd = Node("ALND (or RT) of regional LNs [II, B]")

neoadjuvant_therapies = [ Node("Follow Figures 4-7 for neoadjuvant therapy",
    children = [
        Node("ycN0/ypN0 after neoadjuvant ChT",
            condition = dc.contains("n_status_residual", ("ycN0", "ypN0")),
            children = [
                Node("SLN- or TAD-",
                    condition = dc.any_of(dc.is_false("sln_positive"), dc.is_false("tad_positive")),
                    children = [
                        Node("Consider RT if pN+ at primary diagnosis [II, B]")
                    ]
                ),
                Node("SLN+ or TAD+",
                    condition = dc.any_of(dc.is_true("sln_positive"), dc.is_true("tad_positive")),
                    children = [ alnd ]
                ),
            ]
        ),
        Node("ycN+/ypN+ after neoadjuvant ChT",
            condition = dc.contains("n_status_residual", ("ycN+", "ypN+")),
            children = [ alnd ]
        ),
    ]
) ]

neoadjuvant_indicated = Node("PST indicated",
    condition = dc.is_true("neoadjuvant"),
    children = [
        Node("cN0/pN0 at primary diagnosis",
            condition = dc.contains("n_status", ("cN0", "pN0")),
            children = neoadjuvant_therapies
        ),
        Node("cN+/pN+ at primary diagnosis",
            condition = dc.contains("n_status", ("cN+", "pN+")),
            children = neoadjuvant_therapies
        ),
    ]
)

graph = Node(
    "EBC-ALN",
    children = [surgery_indicated, neoadjuvant_indicated]
)

examples = [
    Data(neoadjuvant=False, n_status = "iN+", positive_nodes=3),
    Data(neoadjuvant=False, n_status = "cN+", positive_nodes=1),
    Data(neoadjuvant=False, n_status = "cN+", positive_nodes=1),
    Data(neoadjuvant=True, n_status = "cN0"),
]

for x in examples:
    print(dg.walk(graph, x))

