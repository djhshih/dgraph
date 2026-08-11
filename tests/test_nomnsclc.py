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
ECOG_HUB = "ECOG_PS_and_PD-L1_expression_level"
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
PATIENTS = load_patient_cases(ROOT / "demo/patients/nomnsclc/nsqnscc_ici.json")
SCHEMA = infer_schema(graph)


def case(case_id: str):
    return build_patient(SCHEMA, case_by_id(PATIENTS, case_id))


class NomnsclcNsqnsccIciSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(graph),
            {
                "Oligometastatic": "tag",
                "PS": "unknown",
                "pdl1_percent": "unknown",
                "any_expression_of_PD-L1": "tag",
            },
        )


class NomnsclcNsqnsccIciWalkTests(unittest.TestCase):
    def test_example_1_empty_stops_at_ps_pdl1_frontier(self):
        x = case("example_1_empty")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[ROOT_LABEL, ECOG_HUB]],
                ["PS", "pdl1_percent", "any_expression_of_PD-L1"],
            ),
        )

    def test_example_2_oligometastatic_reaches_lrt_and_ps_pdl1_frontier(self):
        x = case("example_2_oligometastatic")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [
                    [ROOT_LABEL, "Oligometastatic", LRT],
                    [ROOT_LABEL, ECOG_HUB],
                ],
                ["PS", "pdl1_percent", "any_expression_of_PD-L1"],
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
                    ECOG_HUB,
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
                    ECOG_HUB,
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
                    ECOG_HUB,
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
                [[ROOT_LABEL, ECOG_HUB, ">= 3 PS and <= 4 PS", BSC]],
                [],
            ),
        )


class NomnsclcNsqnsccIciEquivalenceTests(unittest.TestCase):
    """Hub uses always() in curated; DOT keeps has(tag). Numeric PS/pdl1 also diverge."""

    def test_curated_ecog_always_diverges_from_dot_tag(self):
        dot_graph = dot_to_graph(DOT.read_text())
        x = case("example_1_empty")
        curated_paths, curated_required = walk(graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_paths[0].path[-1].label, ECOG_HUB)
        self.assertIn("PS", curated_required)
        self.assertEqual(dot_paths[0].path[-1].label, ROOT_LABEL)
        self.assertIn(ECOG_HUB, dot_required)

    def test_curated_numeric_ps_pdl1_diverges_from_dot_tag_conditions(self):
        dot_graph = dot_to_graph(DOT.read_text())
        x = case("example_3_pdl1_high")
        curated_paths, curated_required = walk(graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, AFTER_ICI)
        self.assertEqual(dot_paths[0].path[-1].label, ROOT_LABEL)
        self.assertIn(ECOG_HUB, dot_required)


# --- Stage IV NSqNSCC with contraindication for immunotherapy ---

NO_ICI_DG = ROOT / "data/nomnsclc/dg/nsqnscc_no_ici_curated.dg"
NO_ICI_DOT = ROOT / "data/nomnsclc/dot/nsqnscc_no_ici.dot"

NO_ICI_ROOT = (
    "Stage IV NSqNSCC, molecular tests "
    "(EGFR/ALK/ROS1/BRAF/RET/MET/EGFR ex20ins/KRAS G12C/NTRK/HER2) negative, "
    "with contraindication for immunotherapy"
)
NO_ICI_ECOG = "ECOG_PS"
NO_ICI_LRT = "Systemic therapy and LRT [II, B]"
NO_ICI_PS0_TX = (
    "Platinum-doublet ChT [I, A] (pemetrexed preferred) [II, A; MCBS 4] followed by "
    "pemetrexed maintenance [I, A; MCBS 4]; if pemetrexed switch maintenance [I, B]; "
    "if 4 cycles of gemcitabine-cisplatin: gemcitabine continuation maintenance [I, C]\n"
    "Platinum-doublet ChT [I, A] (pemetrexed preferred) [II, A; MCBS 4]\n"
    "Carboplatin-paclitaxel-bevacizumab followed by bevacizumab maintenance [I, A; MCBS 2]\n"
    "Or platinum-pemetrexed-bevacizumab followed by pemetrexed-bevacizumab maintenance [I, A]"
)
NO_ICI_PS2_TX = (
    "Platinum-doublet ChT [carboplatin preferred: I, A; pemetrexed preferred: II, A]\n"
    "Maintenance pemetrexed if improvement to PS 0-1 [MCBS 4]\n"
    "Single-agent ChT (pemetrexed, gemcitabine, vinorelbine, docetaxel) [I, B]"
)
NO_ICI_SECOND_LINE = (
    "Pemetrexed [I, B]\n"
    "Docetaxel [I, B]\n"
    "Nintedanib-docetaxel [II, B]\n"
    "Ramucirumab-docetaxel [I, B; MCBS 1]"
)

no_ici_graph = load_dg(NO_ICI_DG)
NO_ICI_PATIENTS = load_patient_cases(
    ROOT / "demo/patients/nomnsclc/nsqnscc_no_ici.json"
)
NO_ICI_SCHEMA = infer_schema(no_ici_graph)


def no_ici_case(case_id: str):
    return build_patient(NO_ICI_SCHEMA, case_by_id(NO_ICI_PATIENTS, case_id))


class NomnsclcNsqnsccNoIciSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(no_ici_graph),
            {
                "Oligometastatic": "tag",
                "PS": "unknown",
            },
        )


class NomnsclcNsqnsccNoIciWalkTests(unittest.TestCase):
    def test_example_1_empty_stops_at_ps_frontier(self):
        x = no_ici_case("example_1_empty")
        self.assertEqual(validate_data(NO_ICI_SCHEMA, x), [])
        self.assertEqual(
            walk(no_ici_graph, x),
            (
                [[NO_ICI_ROOT, NO_ICI_ECOG]],
                ["PS"],
            ),
        )

    def test_example_2_oligometastatic_reaches_lrt_and_ps_frontier(self):
        x = no_ici_case("example_2_oligometastatic")
        self.assertEqual(validate_data(NO_ICI_SCHEMA, x), [])
        self.assertEqual(
            walk(no_ici_graph, x),
            (
                [
                    [NO_ICI_ROOT, "Oligometastatic", NO_ICI_LRT],
                    [NO_ICI_ROOT, NO_ICI_ECOG],
                ],
                ["PS"],
            ),
        )

    def test_example_3_ps0_reaches_second_line(self):
        x = no_ici_case("example_3_ps0")
        self.assertEqual(validate_data(NO_ICI_SCHEMA, x), [])
        self.assertEqual(
            walk(no_ici_graph, x),
            (
                [[
                    NO_ICI_ROOT,
                    NO_ICI_ECOG,
                    ">= 0 PS and <= 1 PS",
                    NO_ICI_PS0_TX,
                    "Disease progression",
                    ">= 0 PS and <= 2 PS",
                    NO_ICI_SECOND_LINE,
                ]],
                [],
            ),
        )

    def test_example_4_ps2_reaches_second_line(self):
        x = no_ici_case("example_4_ps2")
        self.assertEqual(validate_data(NO_ICI_SCHEMA, x), [])
        self.assertEqual(
            walk(no_ici_graph, x),
            (
                [[
                    NO_ICI_ROOT,
                    NO_ICI_ECOG,
                    "= 2 PS",
                    NO_ICI_PS2_TX,
                    "Disease progression",
                    ">= 0 PS and <= 2 PS",
                    NO_ICI_SECOND_LINE,
                ]],
                [],
            ),
        )

    def test_example_5_ps4_best_supportive_care(self):
        x = no_ici_case("example_5_ps4_bsc")
        self.assertEqual(validate_data(NO_ICI_SCHEMA, x), [])
        self.assertEqual(
            walk(no_ici_graph, x),
            (
                [[NO_ICI_ROOT, NO_ICI_ECOG, ">= 3 PS and <= 4 PS", BSC]],
                [],
            ),
        )


class NomnsclcNsqnsccNoIciEquivalenceTests(unittest.TestCase):
    """ECOG_PS uses always() in curated; DOT keeps has('ECOG_PS'). Numeric PS also diverges."""

    def test_curated_ecog_always_diverges_from_dot_tag(self):
        dot_graph = dot_to_graph(NO_ICI_DOT.read_text())
        x = no_ici_case("example_1_empty")
        curated_paths, curated_required = walk(no_ici_graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_paths[0].path[-1].label, NO_ICI_ECOG)
        self.assertEqual(curated_required, ["PS"])
        self.assertEqual(dot_paths[0].path[-1].label, NO_ICI_ROOT)
        self.assertIn("ECOG_PS", dot_required)

    def test_curated_numeric_ps_diverges_from_dot_tag_conditions(self):
        dot_graph = dot_to_graph(NO_ICI_DOT.read_text())
        x = no_ici_case("example_3_ps0")
        curated_paths, curated_required = walk(no_ici_graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, NO_ICI_SECOND_LINE)
        self.assertEqual(dot_paths[0].path[-1].label, NO_ICI_ROOT)
        self.assertIn("ECOG_PS", dot_required)


if __name__ == "__main__":
    unittest.main()
