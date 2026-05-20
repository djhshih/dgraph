# Early breast cancer treatment overview
# Figure 2, Loibl et al., 2024, https://doi.org/10.1016/j.annonc.2023.11.016

import os, sys

from dataclasses import dataclass, replace

sys.path.append(os.path.abspath('..'))
import dgraph.graph as dg
import dgraph.condition as dc
from dgraph.graph import Node

@dataclass
class Data(dg.Data):
    hr_status: bool
    her2_status: bool
    t_status: str
    n_status: str
    m_status: str = "M0"
    postmenopausal: bool = False
    receiving_ofs: bool = False

surgery = Node("Primary surgery +/- RT")
neoadjuvant = Node("Neoadjuvant therapy")
systemic = Node("Systemic treatment")

# Figure 2 from ESMO 2024 Early breast cancer guidelines
graph = Node('EBC',
    children = [
        Node("HR+",
            condition = dc.is_true("hr_status"),
            children = [Node("ET [I, A]")]
        ),
        Node("Premenopausal patients receiving OFS and postmenopausal patients",
            condition = dc.any_of(
                dc.is_true("postmenopausal"),
                dc.all_of(dc.is_false("postmenopausal"), dc.is_true("receiving_ofs")),
            ),
            children = [Node("Adjuvant bisphosphonates [I, A]")]
        ),
        Node("HR+/HER-",
             condition = dc.all_of(dc.is_true("hr_status"), dc.is_false("her2_status")),
             children = [ replace(neoadjuvant, children = [ replace(surgery, children = [systemic]) ]) ],
        ),
        Node("HER2+",
            condition = dc.is_true("her2_status"),
            children = [
                Node("cT1 N0",
                    condition = dc.all_of(dc.equals("t_status", "T1"), dc.equals("n_status", "N0")),
                    children = [ replace(surgery, children = [systemic]) ],
                ),
                Node(">=cT2 or cN+",
                    condition = dc.any_of(dc.contains("t_status", ("T2", "T3", "T4")), dc.equals("n_status", "N+")),
                    children = [ replace(neoadjuvant, children = [ replace(surgery, children = [systemic]) ]) ],
                ),
            ],
        ),
        Node("TNBC",
            condition = dc.all_of(dc.is_false("hr_status"), dc.is_false("her2_status")),
            children = [
                Node("cT1a or cT1b N0",
                    condition = dc.all_of(dc.contains("t_status", ("T1a", "T1b")), dc.equals("n_status", "N0")),
                    children = [ replace(surgery, children = [systemic]) ],
                ),
                Node("cT1c-4 or N+",
                    condition = dc.any_of(dc.contains("t_status", ("T1c", "T2", "T3", "T4")), dc.equals("n_status", "N+")),
                    children = [ replace(neoadjuvant, children = [ replace(surgery, children = [systemic]) ]) ],
                ),
            ]
        ),
    ]
)

x = Data(her2_status=True, hr_status=False, t_status = "T1", n_status = "N0")
print(dg.walk(graph, x))

x = Data(her2_status=False, hr_status=False, t_status = "T1a", n_status = "N0")
print(dg.walk(graph, x))

x = Data(her2_status=False, hr_status=False, t_status = "T1a", n_status = "N+")
print(dg.walk(graph, x))

x = Data(her2_status=True, hr_status=False, t_status = "T1", n_status = "N+")
print(dg.walk(graph, x))

xb = Data(her2_status=False, hr_status=True, t_status = "T1", n_status = "N0")
print(dg.walk(graph, xb))

