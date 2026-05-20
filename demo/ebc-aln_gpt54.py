# Management of ALN involvement in early breast cancer
# Figure 3, Loibl et al., 2024, https://doi.org/10.1016/j.annonc.2023.11.016

import os, sys

from dataclasses import dataclass

sys.path.append(os.path.abspath('..'))
from dgraph.graph import Node, walk


@dataclass
class Data:
    # Pathology / timing
    neoadjuvant: bool = False
    pathological_node_positive: bool = False   # pN+

    # Upfront-surgery branch
    z0011_criteria_met: bool = False
    positive_lns: int = 0

    # Neoadjuvant branch
    clinical_node_positive_at_diagnosis: bool = False   # cN+/iN+
    residual_nodal_disease: bool = False                # ypN+
    tad_positive: bool = False


graph = Node(
    "Management of ALN involvement in EBC",
    children=[
        Node(
            "pN+",
            condition=lambda x: x.pathological_node_positive,
            children=[
                Node(
                    "upfront surgery",
                    condition=lambda x: not x.neoadjuvant,
                    children=[
                        Node(
                            "ACOSOG-Z0011 criteria met and <=2 positive LNs",
                            condition=lambda x: x.z0011_criteria_met and x.positive_lns <= 2,
                            children=[
                                Node("No further locoregional treatment"),
                                Node("RT (basis axilla) [II, B]"),
                            ],
                        ),
                        Node(
                            "ACOSOG-Z0011 criteria not met or >2 positive LNs",
                            condition=lambda x: (not x.z0011_criteria_met) or x.positive_lns > 2,
                            children=[
                                Node("RT (axilla) [IV, B]"),
                                Node("ALND [I, A]"),
                            ],
                        ),
                    ],
                ),
                Node(
                    "after neoadjuvant ChT",
                    condition=lambda x: x.neoadjuvant,
                    children=[
                        Node(
                            "cN0/pN0 at primary diagnosis",
                            condition=lambda x: not x.clinical_node_positive_at_diagnosis,
                            children=[
                                Node("Follow Figures 4-7 for neoadjuvant therapy according to biological subtype"),
                            ],
                        ),
                        Node(
                            "cN+/iN+ at primary diagnosis",
                            condition=lambda x: x.clinical_node_positive_at_diagnosis,
                            children=[
                                Node(
                                    "SLN- or TAD-",
                                    condition=lambda x: not x.residual_nodal_disease and not x.tad_positive,
                                    children=[
                                        Node("Consider RT if pN+ at primary diagnosis [II, B]"),
                                    ],
                                ),
                                Node(
                                    "SLN+ or TAD+",
                                    condition=lambda x: x.residual_nodal_disease or x.tad_positive,
                                    children=[
                                        Node("ALND (or RT) of regional LNs [II, B]"),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
    ],
)


examples = [
    Data(pathological_node_positive=True, neoadjuvant=False, z0011_criteria_met=True, positive_lns=2),
    Data(pathological_node_positive=True, neoadjuvant=False, z0011_criteria_met=False, positive_lns=1),
    Data(pathological_node_positive=True, neoadjuvant=True, clinical_node_positive_at_diagnosis=False),
    Data(pathological_node_positive=True, neoadjuvant=True, clinical_node_positive_at_diagnosis=True, residual_nodal_disease=False, tad_positive=False),
    Data(pathological_node_positive=True, neoadjuvant=True, clinical_node_positive_at_diagnosis=True, residual_nodal_disease=True),
]

for x in examples:
    print(walk(graph, x))
