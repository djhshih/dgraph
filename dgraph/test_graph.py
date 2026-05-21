import unittest

import dgraph.condition as dc
from dgraph.graph import Data, Node, branch, chain, node, walk


surgery_systemic = chain("Primary surgery +/- RT", "Systemic treatment")
neoadjuvant_surgery_systemic = chain("Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment")

# Figure 2 from ESMO 2024 Early breast cancer guidelines
graph = node(
    "EBC",
    branch("HR+", dc.has("HR+"), Node("ET [I, A]")),
    branch(
        "Premenopausal patients receiving OFS and postmenopausal patients",
        dc.any_of(
            dc.has("postmenopausal"),
            dc.all_of(dc.has("premenopausal"), dc.has("receiving_ofs")),
        ),
        Node("Adjuvant bisphosphonates [I, A]"),
    ),
    branch(
        "HR+/HER-",
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


class WalkExamplesTest(unittest.TestCase):
    def test_example_1_her2_t1_n0(self):
        x = Data(("HER2+", "HR-", "T1", "N0"))
        self.assertEqual(
            walk(graph, x),
            [["EBC", "HER2+", "cT1 N0", "Primary surgery +/- RT", "Systemic treatment"]],
        )

    def test_example_2_tnbc_t1a_n0(self):
        x = Data(("HER2-", "HR-", "T1a", "N0"))
        self.assertEqual(
            walk(graph, x),
            [["EBC", "TNBC", "cT1a or cT1b N0", "Primary surgery +/- RT", "Systemic treatment"]],
        )

    def test_example_3_tnbc_t1a_n_plus(self):
        x = Data(("HER2-", "HR-", "T1a", "N+"))
        self.assertEqual(
            walk(graph, x),
            [["EBC", "TNBC", "cT1c-4 or N+", "Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment"]],
        )

    def test_example_4_her2_t1_n_plus(self):
        x = Data(("HER2+", "HR-", "T1", "N+"))
        self.assertEqual(
            walk(graph, x),
            [["EBC", "HER2+", ">=cT2 or cN+", "Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment"]],
        )

    def test_example_5_hr_positive_her2_negative(self):
        xb = Data(("HER2-", "HR+", "T1", "N0"))
        self.assertEqual(
            walk(graph, xb),
            [
                ["EBC", "HR+", "ET [I, A]"],
                ["EBC", "HR+/HER-", "Neoadjuvant therapy", "Primary surgery +/- RT", "Systemic treatment"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
