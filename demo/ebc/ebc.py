# Early breast cancer treatment overview
# Figure 2, Loibl et al., 2024, https://doi.org/10.1016/j.annonc.2023.11.016

import os, sys

from dataclasses import dataclass

sys.path.append(os.path.abspath('..'))
import dgraph.graph as dg
import dgraph.condition as dc
from dgraph.graph import branch, chain, node


@dataclass
class Data(dg.Data):
    hr_status: bool = None
    her2_status: bool = None
    t_status: str = None
    n_status: str = None
    postmenopausal: bool = None
    receiving_ofs: bool = None
    m_status: str = None


surgery_systemic = chain("Primary surgery +/- RT", "Systemic treatment")
neoadjuvant_surgery_systemic = chain("Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment")

# Figure 2 from ESMO 2024 Early breast cancer guidelines
graph = node(
    "EBC",
    branch("HR+", dc.is_true("hr_status"), node("ET [I, A]")),
    branch(
        "Premenopausal patients receiving OFS and postmenopausal patients",
        dc.any_of(
            dc.is_true("postmenopausal"),
            dc.all_of(dc.is_false("postmenopausal"), dc.is_true("receiving_ofs")),
        ),
        node("Adjuvant bisphosphonates [I, A]"),
    ),
    branch(
        "HR+/HER-",
        dc.all_of(dc.is_true("hr_status"), dc.is_false("her2_status")),
        neoadjuvant_surgery_systemic,
    ),
    branch(
        "HER2+",
        dc.is_true("her2_status"),
        branch(
            "cT1 N0",
            dc.all_of(dc.equals("t_status", "T1"), dc.equals("n_status", "N0")),
            surgery_systemic,
        ),
        branch(
            ">=cT2 or cN+",
            dc.any_of(dc.is_in("t_status", ("T2", "T3", "T4")), dc.equals("n_status", "N+")),
            neoadjuvant_surgery_systemic,
        ),
    ),
    branch(
        "TNBC",
        dc.all_of(dc.is_false("hr_status"), dc.is_false("her2_status")),
        branch(
            "cT1a or cT1b N0",
            dc.all_of(dc.is_in("t_status", ("T1a", "T1b")), dc.equals("n_status", "N0")),
            surgery_systemic,
        ),
        branch(
            "cT1c-4 or N+",
            dc.any_of(dc.is_in("t_status", ("T1c", "T2", "T3", "T4")), dc.equals("n_status", "N+")),
            neoadjuvant_surgery_systemic,
        ),
    ),
)

schema = dg.infer_schema(graph)
print(schema)

x = Data(her2_status=True, hr_status=False)
print(dg.validate_data(schema, x))
print(dg.walk(graph, x))

x = Data(her2_status=True, hr_status=False, t_status="T1", n_status="N0")
print(dg.validate_data(schema, x))
print(dg.walk(graph, x))

x = Data(her2_status=False, hr_status=False, t_status="T1a", n_status="N0")
print(dg.validate_data(schema, x))
print(dg.walk(graph, x))

x = Data(her2_status=False, hr_status=False, t_status="T1a", n_status="N+")
print(dg.validate_data(schema, x))
print(dg.walk(graph, x))

x = Data(her2_status=True, hr_status=False, t_status="T1", n_status="N+")
print(dg.validate_data(schema, x))
print(dg.walk(graph, x))

xb = Data(her2_status=False, hr_status=True, t_status="T1", n_status="N0")
print(dg.validate_data(schema, xb))
print(dg.walk(graph, xb))
