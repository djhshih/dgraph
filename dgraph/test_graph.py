import unittest
from dataclasses import dataclass

import dgraph.condition as dc
from dgraph.graph import Node, branch, chain, node, walk


@dataclass
class Data:
    hr_status: bool
    her2_status: bool
    t_status: str
    n_status: str
    m_status: str = "M0"
    postmenopausal: bool = False
    receiving_ofs: bool = False


surgery_systemic = chain("Primary surgery +/- RT", "Systemic treatment")
neoadjuvant_surgery_systemic = chain("Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment")

# Figure 2 from ESMO 2024 Early breast cancer guidelines
graph = node(
    "EBC",
    branch("HR+", dc.is_true("hr_status"), Node("ET [I, A]")),
    branch(
        "Premenopausal patients receiving OFS and postmenopausal patients",
        dc.any_of(
            dc.is_true("postmenopausal"),
            dc.all_of(dc.is_false("postmenopausal"), dc.is_true("receiving_ofs")),
        ),
        Node("Adjuvant bisphosphonates [I, A]"),
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


class WalkExamplesTest(unittest.TestCase):
    def test_example_1_her2_t1_n0(self):
        x = Data(her2_status=True, hr_status=False, t_status="T1", n_status="N0")
        self.assertEqual(
            walk(graph, x),
            [["EBC", "HER2+", "cT1 N0", "Primary surgery +/- RT", "Systemic treatment"]],
        )

    def test_example_2_tnbc_t1a_n0(self):
        x = Data(her2_status=False, hr_status=False, t_status="T1a", n_status="N0")
        self.assertEqual(
            walk(graph, x),
            [["EBC", "TNBC", "cT1a or cT1b N0", "Primary surgery +/- RT", "Systemic treatment"]],
        )

    def test_example_3_tnbc_t1a_n_plus(self):
        x = Data(her2_status=False, hr_status=False, t_status="T1a", n_status="N+")
        self.assertEqual(
            walk(graph, x),
            [["EBC", "TNBC", "cT1c-4 or N+", "Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment"]],
        )

    def test_example_4_her2_t1_n_plus(self):
        x = Data(her2_status=True, hr_status=False, t_status="T1", n_status="N+")
        self.assertEqual(
            walk(graph, x),
            [["EBC", "HER2+", ">=cT2 or cN+", "Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment"]],
        )

    def test_example_5_hr_positive_her2_negative(self):
        xb = Data(her2_status=False, hr_status=True, t_status="T1", n_status="N0")
        self.assertEqual(
            walk(graph, xb),
            [
                ["EBC", "HR+", "ET [I, A]"],
                ["EBC", "HR+/HER-", "Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
