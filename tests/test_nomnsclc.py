import unittest
from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.dot.interpret import dot_to_graph
from dgraph.graph import walk
from dgraph.patient_data import build_patient, case_by_id, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[1]
DG = ROOT / "data/nomnsclc/dg/nsqnscc_ici_curated.dg"
DOT = ROOT / "data/nomnsclc/dot/nsqnscc_ici.dot"

ROOT_LABEL = (
    "Stage IV NSqNSCC, molecular tests negative "
    "(EGFR/ALK/ROS1/BRAF/RET/MET/EGFR ex20ins/KRAS G12C/NTRK/HER2), "
    "without contraindication for immunotherapy"
)
NOT_META = "not_Oligometastatic"
LRT = "Systemic therapy & LRT [II, B]"
BSC = "Best Supportive Care alone [III, A]"
ICI_MONO = (
    "Pembrolizumab [I, A; MCBS 5]\n"
    "Atezolizumab (also for ICs >=10%) [I, A; MCBS 5]\n"
    "Cemiplimab [I, A; MCBS 4] (for PS 2 for all drugs: [III, B])"
)
CHT_ICI = (
    "Pembrolizumab-platinum-pemetrexed (4 cycles) followed by pembrolizumab-pemetrexed [I, A; MCBS 4]\n"
    "Atezolizumab-carboplatin-nab-paclitaxel (4-6 cycles) followed by atezolizumab [I, A; MCBS 3]\n"
    "Atezolizumab-bevacizumab-carboplatin-paclitaxel (4-6 cycles) followed by atezolizumab-bevacizumab [I, A; MCBS 3]\n"
    "Nivolumab-ipilimumab + 2 cycles of platinum-doublet ChT followed by nivolumab-ipilimumab [I, A; MCBS 4]\n"
    "Cemiplimab-platinum-doublet ChT (4 cycles) followed by cemiplimab + pemetrexed maintenance [I, A]\n"
    "Durvalumab-tremelimumab-platinum-doublet ChT (4 cycles) followed by durvalumab-tremelimumab "
    "(tremelimumab one additional dose) + pemetrexed maintenance [I, A; MCBS 4]\n"
    "Nivolumab-ipilimumab (only for PD-L1 >=1%) [I, A; MCBS 4]"
)
PS2_CHT = (
    "Platinum-doublet ChT [carboplatin preferred: I, A; pemetrexed preferred: II, A]\n"
    "Maintenance pemetrexed if improvement to PS 0-1 [MCBS 4]\n"
    "Single-agent ChT [pemetrexed: II, B; gemcitabine, vinorelbine or docetaxel: I, B]"
)
AFTER_ICI = (
    "Platinum-doublet ChT [I, A] (pemetrexed preferred) [II, A; MCBS 4] followed by "
    "pemetrexed maintenance [I, A; MCBS 4] if pemetrexed switch maintenance [I, B]\n"
    "If 4 cycles of gemcitabine-cisplatin: gemcitabine continuation maintenance [I, C]\n"
    "Platinum-doublet ChT [I, A] (pemetrexed preferred) [II, A; MCBS 4]\n"
    "Carboplatin-paclitaxel-bevacizumab followed by bevacizumab maintenance [I, A; MCBS 2] "
    "Or platinum-pemetrexed-bevacizumab followed by pemetrexed-bevacizumab maintenance [I, A]\n"
    "Re-challenge ICI [III, B]"
)
AFTER_CHT_ICI = (
    "Pemetrexed [I, B]\n"
    "Docetaxel [I, B]\n"
    "Nintedanib-docetaxel [II, B]\n"
    "Ramucirumab-docetaxel [I, B; MCBS 1]\n"
    "Re-challenge ICI [III, B]"
)
AFTER_CHT = (
    "Nivolumab [I, A; MCBS 5]\n"
    "Atezolizumab [I, A; MCBS 5]\n"
    "Pembrolizumab (PD-L1 >=1%) [I, A; MCBS 5]\n"
    "Other options are the same as for second-line treatment for PS 0-2 after ChT-ICI"
)

graph = load_dg(DG)
PATIENTS = load_patient_cases(ROOT / "fixtures/patients/nomnsclc/nsqnscc_ici.json")
SCHEMA = infer_schema(graph)


def case(case_id: str):
    return build_patient(SCHEMA, case_by_id(PATIENTS, case_id))


TAG_EXAMPLES = [
    case("example_1_empty"),
    case("example_2_oligometastatic"),
]


class NomnsclcNsqnsccIciSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(graph),
            {
                "Oligometastatic": "tag",
                "not_Oligometastatic": "tag",
                "PS": "unknown",
                "pdl1_percent": "unknown",
                "any_expression_of_PD-L1": "tag",
            },
        )


class NomnsclcNsqnsccIciWalkTests(unittest.TestCase):
    def test_example_1_empty_stops_at_oligometastatic_frontier(self):
        x = case("example_1_empty")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[ROOT_LABEL]],
                ["Oligometastatic", "not_Oligometastatic"],
            ),
        )

    def test_example_2_oligometastatic_reaches_lrt_only(self):
        x = case("example_2_oligometastatic")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[ROOT_LABEL, "Oligometastatic", LRT]],
                [],
            ),
        )

    def test_example_3_pdl1_high_reaches_second_line_after_ici(self):
        x = case("example_3_pdl1_high")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    NOT_META,
                    ">= 0 PS and <= 2 PS and >= 50 pdl1_percent",
                    ICI_MONO,
                    "Disease progression",
                    ">= 0 PS and <= 2 PS",
                    AFTER_ICI,
                ]],
                [],
            ),
        )

    def test_example_4_any_pdl1_reaches_second_line_after_cht_ici(self):
        x = case("example_4_any_pdl1")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    NOT_META,
                    ">= 0 PS and <= 1 PS and any_expression_of_PD-L1",
                    CHT_ICI,
                    "Disease progression",
                    ">= 0 PS and <= 2 PS",
                    AFTER_CHT_ICI,
                ]],
                [],
            ),
        )

    def test_example_5_ps2_low_pdl1_reaches_second_line_ici(self):
        x = case("example_5_ps2_low_pdl1")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    NOT_META,
                    "= 2 PS and < 50 pdl1_percent",
                    PS2_CHT,
                    "Disease progression",
                    ">= 0 PS and <= 2 PS",
                    AFTER_CHT,
                ]],
                [],
            ),
        )

    def test_example_6_ps4_best_supportive_care(self):
        x = case("example_6_ps4_bsc")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[ROOT_LABEL, NOT_META, ">= 3 PS and <= 4 PS", BSC]],
                [],
            ),
        )


class NomnsclcNsqnsccIciEquivalenceTests(unittest.TestCase):
    """Tag forks match DOT; numeric PS/pdl1 branches intentionally diverge."""

    def _walk_labels(self, g, x):
        paths, required = walk(g, x)
        return (
            [[node.label for node in path.path] for path in paths],
            required,
        )

    def test_dot_to_graph_matches_curated_dg_on_tag_paths(self):
        dot_graph = dot_to_graph(DOT.read_text())
        for x in TAG_EXAMPLES:
            self.assertEqual(
                self._walk_labels(dot_graph, x),
                self._walk_labels(graph, x),
                msg=f"mismatch for {x}",
            )

    def test_curated_numeric_ps_pdl1_diverges_from_dot_tag_conditions(self):
        dot_graph = dot_to_graph(DOT.read_text())
        x = case("example_3_pdl1_high")
        curated_paths, curated_required = walk(graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, AFTER_ICI)
        self.assertEqual(dot_paths[0].path[-1].label, NOT_META)
        self.assertTrue(
            any(r in {"PS", ">=0", "<=2", ">=50", "pdl1_percent"} for r in dot_required)
        )


if __name__ == "__main__":
    unittest.main()
