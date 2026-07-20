import unittest
from pathlib import Path

import dgraph.graph as dg
from dgraph.dg_loader import load_dg
from dgraph.dot.interpret import dot_to_graph
from dgraph.graph import walk
from dgraph.schema import infer_schema, validate_data
from dgraph.patient_data import build_patient, case_by_id, load_patient_cases

ROOT = Path(__file__).resolve().parents[1]
DG = ROOT / "data/elansclc/dg/locoregional_staging_curated.dg"
DOT = ROOT / "data/elansclc/dot/locoregional_staging.dot"

ROOT_LABEL = "Stage I NSCLC"
PREOP = "Preoperative evaluation and MDT discussion"
SURGERY = "Surgery [III, A]\nSublobar resection\nLobectomy"
SURVEILLANCE = "Surveillance [I, A]"
OSIMERTINIB = "Osimertinib for 3 years [I, A; MCBS A (AT)]"
PORT = "Definitive PORT (60 Gy in 30 fractions) [III, C]"


graph = load_dg(DG)

LOC_PATIENTS = load_patient_cases(ROOT / "data/elansclc/patient/locoregional_staging.json")
LOC_SCHEMA = infer_schema(graph)


def loc_case(case_id: str):
    return build_patient(LOC_SCHEMA, case_by_id(LOC_PATIENTS, case_id))


EXAMPLES = [
    loc_case("example_1_no_tags"),
    loc_case("example_2_medically_inoperable"),
    loc_case("example_3_medically_operable"),
    loc_case("equivalence_tag_example_r2"),
    loc_case("equivalence_tag_example_r1"),
    loc_case("equivalence_tag_example_higher_stage"),
]


class ElansclcLocoregionalStagingSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(graph),
            {
                "Medically_inoperable": "tag",
                "Medically_operable": "tag",
                "R2": "tag",
                "R1": "tag",
                "R0": "tag",
                "tumour_size_cm": "unknown",
                "N0": "tag",
                "EGFR_WT": "tag",
                "EGFR_exon_19_deletion": "tag",
                "L858R": "tag",
                "Higher_stage": "tag",
            },
        )


class ElansclcLocoregionalStagingWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_operability_frontier(self):
        x = loc_case("example_1_no_tags")
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[ROOT_LABEL, PREOP]],
                ["Medically_inoperable", "Medically_operable"],
            ),
        )

    def test_example_2_medically_inoperable_reaches_surveillance(self):
        x = loc_case("example_2_medically_inoperable")
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    PREOP,
                    "Medically_inoperable",
                    "SBRT [II, A]",
                    "Surveillance",
                    "Local_progression",
                    "Salvage surgery [IV, B]",
                    SURVEILLANCE,
                ]],
                [],
            ),
        )

    def test_example_3_medically_operable_stops_at_margin_frontier(self):
        x = loc_case("example_3_medically_operable")
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[ROOT_LABEL, PREOP, "Medically_operable", SURGERY]],
                ["R2", "R1", "R0"],
            ),
        )

    def test_example_4_r0_small_tumour_to_surveillance(self):
        x = loc_case("example_4_r0_small_tumour")
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    PREOP,
                    "Medically_operable",
                    SURGERY,
                    "R0",
                    "< 3 tumour_size_cm  and N0",
                    SURVEILLANCE,
                ]],
                [],
            ),
        )

    def test_example_5_r0_t3_4_egfr_mutation_osimertinib(self):
        x = loc_case("example_5_r0_tumour_3_4cm_egfr_mutated")
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    PREOP,
                    "Medically_operable",
                    SURGERY,
                    "R0",
                    ">= 3 tumour_size_cm and <= 4 tumour_size_cm and N0",
                    "EGFR_exon_19_deletion or L858R",
                    OSIMERTINIB,
                    SURVEILLANCE,
                ]],
                [],
            ),
        )

    def test_example_6_r1_port_to_surveillance(self):
        x = loc_case("example_6_r1_port")
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    PREOP,
                    "Medically_operable",
                    SURGERY,
                    "R1",
                    PORT,
                    SURVEILLANCE,
                ]],
                [],
            ),
        )


class ElansclcLocoregionalStagingEquivalenceTests(unittest.TestCase):
    """Tag-path walks match DOT; tumour_size_cm branches intentionally diverge (lt/ge/le vs has tags)."""

    def _walk_labels(self, g, x):
        paths, required = walk(g, x)
        return (
            [[node.label for node in path.path] for path in paths],
            required,
        )

    def test_dot_to_graph_matches_curated_dg_on_tag_paths(self):
        dot_graph = dot_to_graph(DOT.read_text())
        for x in EXAMPLES:
            self.assertEqual(
                self._walk_labels(dot_graph, x),
                self._walk_labels(graph, x),
                msg=f"mismatch for {x}",
            )

    def test_curated_numeric_tumour_size_diverges_from_dot_tag_conditions(self):
        dot_graph = dot_to_graph(DOT.read_text())
        x = loc_case("example_4_r0_small_tumour")
        curated_paths, curated_required = walk(graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, SURVEILLANCE)
        self.assertIn("<3", dot_required)
        self.assertIn("tumour_size_cm", dot_required)
        self.assertEqual(dot_paths[0].path[-1].label, "R0")


# --- Resectable stage II-III NSCLC ---

RESECTABLE_DG = ROOT / "data/elansclc/dg/resectable.dg"
RESECTABLE_DOT = ROOT / "data/elansclc/dot/resectable.dot"

RESECTABLE_ROOT = "Resectable stage II-III NSCLC"
RESECTABLE_WORKUP = (
    "EGFR, ALK and PD-L1 testing\nPreoperative evaluation and MDT discussion"
)
RESECTABLE_SURGERY = "Surgery [III, A]"
RESECTABLE_SURVEILLANCE = "Surveillance [I, A]"
ATEZO_PEMBRO = (
    "Atezolizumab for 1 year [I, A; MCBS A (AT)]\n"
    "Pembrolizumab for 1 year [I, A; MCBS A (AT)]"
)
ALECTINIB = "Alectinib for 2 years [I, A; MCBS A]"

resectable_graph = load_dg(RESECTABLE_DG)

RESECTABLE_PATIENTS = load_patient_cases(
    ROOT / "data/elansclc/patient/resectable.json"
)
RESECTABLE_SCHEMA = infer_schema(resectable_graph)


def resect_case(case_id: str):
    return build_patient(
        RESECTABLE_SCHEMA,
        case_by_id(RESECTABLE_PATIENTS, case_id),
    )


RESECTABLE_EXAMPLES = [
    resect_case("example_1_no_tags"),
    resect_case("example_2_egfr_alk_wt"),
    resect_case("example_3_cht_ici_ineligible"),
    resect_case("example_4_cht_ici_eligible"),
    resect_case("example_5_pdl1_positive"),
    resect_case("example_6_alk_rearrangement"),
]


class ElansclcResectableSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(resectable_graph),
            {
                "EGFR_WT": "tag",
                "ALK_WT": "tag",
                "ChT-ICI_ineligible": "tag",
                "R1": "tag",
                "R2": "tag",
                "R0": "tag",
                "ChT_eligible": "tag",
                "PD-L1_positive": "tag",
                "PD-L1_negative": "tag",
                "ChT_ineligible": "tag",
                "ChT-ICI_eligible": "tag",
                "EGFR_mutation": "tag",
                "ALK_rearrangement": "tag",
                "EGFR_exon_19_deletion": "tag",
                "L858R": "tag",
            },
        )


class ElansclcResectableWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_biomarker_frontier(self):
        x = resect_case("example_1_no_tags")
        self.assertEqual(validate_data(infer_schema(resectable_graph), x), [])
        self.assertEqual(
            walk(resectable_graph, x),
            (
                [[RESECTABLE_ROOT, RESECTABLE_WORKUP]],
                ["EGFR_WT", "ALK_WT", "EGFR_mutation", "ALK_rearrangement"],
            ),
        )

    def test_example_2_wt_stops_at_cht_ici_frontier(self):
        x = resect_case("example_2_egfr_alk_wt")
        self.assertEqual(validate_data(infer_schema(resectable_graph), x), [])
        self.assertEqual(
            walk(resectable_graph, x),
            (
                [[RESECTABLE_ROOT, RESECTABLE_WORKUP, "EGFR_WT and ALK_WT"]],
                ["ChT-ICI_ineligible", "ChT-ICI_eligible"],
            ),
        )

    def test_example_3_cht_ici_ineligible_stops_at_margin_frontier(self):
        x = resect_case("example_3_cht_ici_ineligible")
        self.assertEqual(validate_data(infer_schema(resectable_graph), x), [])
        self.assertEqual(
            walk(resectable_graph, x),
            (
                [[
                    RESECTABLE_ROOT,
                    RESECTABLE_WORKUP,
                    "EGFR_WT and ALK_WT",
                    "ChT-ICI_ineligible",
                    RESECTABLE_SURGERY,
                ]],
                ["R1", "R2", "R0"],
            ),
        )

    def test_example_4_cht_ici_eligible_to_surveillance(self):
        x = resect_case("example_4_cht_ici_eligible")
        self.assertEqual(validate_data(infer_schema(resectable_graph), x), [])
        self.assertEqual(
            walk(resectable_graph, x),
            (
                [[
                    RESECTABLE_ROOT,
                    RESECTABLE_WORKUP,
                    "EGFR_WT and ALK_WT",
                    "ChT-ICI_eligible",
                    "ChT-ICI [I, A]",
                    RESECTABLE_SURGERY,
                    "Immunotherapy (selected regimens) [I, A]",
                    RESECTABLE_SURVEILLANCE,
                ]],
                [],
            ),
        )

    def test_example_5_adjuvant_pdl1_positive_to_surveillance(self):
        x = resect_case("example_5_pdl1_positive")
        self.assertEqual(validate_data(infer_schema(resectable_graph), x), [])
        self.assertEqual(
            walk(resectable_graph, x),
            (
                [[
                    RESECTABLE_ROOT,
                    RESECTABLE_WORKUP,
                    "EGFR_WT and ALK_WT",
                    "ChT-ICI_ineligible",
                    RESECTABLE_SURGERY,
                    "R0",
                    "ChT_eligible",
                    "Cisplatin-based ChT [I, A]",
                    "PD-L1_positive",
                    ATEZO_PEMBRO,
                    RESECTABLE_SURVEILLANCE,
                ]],
                [],
            ),
        )

    def test_example_6_alk_rearrangement_to_alectinib(self):
        x = resect_case("example_6_alk_rearrangement")
        self.assertEqual(validate_data(infer_schema(resectable_graph), x), [])
        self.assertEqual(
            walk(resectable_graph, x),
            (
                [[
                    RESECTABLE_ROOT,
                    RESECTABLE_WORKUP,
                    "EGFR_mutation or ALK_rearrangement",
                    RESECTABLE_SURGERY,
                    "R0",
                    "ALK_rearrangement",
                    "ChT [II, C]",
                    ALECTINIB,
                    RESECTABLE_SURVEILLANCE,
                ]],
                [],
            ),
        )


class ElansclcResectableEquivalenceTests(unittest.TestCase):
    """Full walk equivalence between DOT compiler output and curated `.dg`."""

    def _walk_labels(self, g, x):
        paths, required = walk(g, x)
        return (
            [[node.label for node in path.path] for path in paths],
            required,
        )

    def test_dot_to_graph_matches_curated_dg(self):
        dot_graph = dot_to_graph(RESECTABLE_DOT.read_text())
        for x in RESECTABLE_EXAMPLES:
            self.assertEqual(
                self._walk_labels(dot_graph, x),
                self._walk_labels(resectable_graph, x),
                msg=f"mismatch for {x}",
            )


# --- Unresectable stage III NSCLC (systemic treatment) ---

SYSTEMIC_DG = ROOT / "data/elansclc/dg/systemic_treatment_curated.dg"
SYSTEMIC_DOT = ROOT / "data/elansclc/dot/systemic_treatment.dot"

SYSTEMIC_ROOT = "Unresectable stage III NSCLC"
SYSTEMIC_WORKUP = "EGFR and PD-L1 testing\nMDT discussion"
SYSTEMIC_LEFT = "EGFR_mutation or < 1 pdl1_percent"
SYSTEMIC_RIGHT = "EGFR_WT and > 1 pdl1_percent"
SYSTEMIC_CRT = "Concurrent CRT [I, A]"
SYSTEMIC_OSIMERTINIB = "Osimertinib [I, A; MCBS 4]"
DURVALUMAB_IA = "Durvalumab for 1 year [I, A; MCBS 4]"
SYSTEMIC_SURVEILLANCE = "Surveillance [I, A]"

systemic_graph = load_dg(SYSTEMIC_DG)

SYSTEMIC_PATIENTS = load_patient_cases(
    ROOT / "data/elansclc/patient/systemic_treatment.json"
)
SYSTEMIC_SCHEMA = infer_schema(systemic_graph)


def systemic_case(case_id: str):
    return build_patient(
        SYSTEMIC_SCHEMA,
        case_by_id(SYSTEMIC_PATIENTS, case_id),
    )


SYSTEMIC_EXAMPLES = [
    systemic_case("example_2_egfr_mutation"),
    systemic_case("example_5_crt_eligible_egfr_mut"),
    systemic_case("example_6_osimertinib_path"),
    systemic_case("example_8_rt_surveillance"),
    systemic_case("equivalence_tag_example_egfr_mut_crt"),
    systemic_case("equivalence_tag_example_ineligible_rt"),
]


class ElansclcSystemicTreatmentSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(systemic_graph),
            {
                "EGFR_mutation": "tag",
                "pdl1_percent": "unknown",
                "Concurrent_CRT_eligible": "tag",
                "EGFR_exon_19_deletion": "tag",
                "L858R": "tag",
                "no_EGFR_exon_19_deletion": "tag",
                "no_L858R": "tag",
                "Concurrent_CRT_ineligible": "tag",
                "Sequential_CRT": "tag",
                "RT": "tag",
                "EGFR_WT": "tag",
            },
        )


class ElansclcSystemicTreatmentWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_biomarker_frontier(self):
        x = systemic_case("example_1_no_tags")
        self.assertEqual(validate_data(infer_schema(systemic_graph), x), [])
        self.assertEqual(
            walk(systemic_graph, x),
            (
                [[SYSTEMIC_ROOT, SYSTEMIC_WORKUP]],
                ["EGFR_mutation", "pdl1_percent", "EGFR_WT"],
            ),
        )

    def test_example_2_egfr_mutation_stops_at_crt_frontier(self):
        x = systemic_case("example_2_egfr_mutation")
        self.assertEqual(validate_data(infer_schema(systemic_graph), x), [])
        self.assertEqual(
            walk(systemic_graph, x),
            (
                [[SYSTEMIC_ROOT, SYSTEMIC_WORKUP, SYSTEMIC_LEFT]],
                ["Concurrent_CRT_eligible", "Concurrent_CRT_ineligible"],
            ),
        )

    def test_example_3_low_pdl1_enters_left_branch(self):
        x = systemic_case("example_3_low_pdl1")
        self.assertEqual(validate_data(infer_schema(systemic_graph), x), [])
        self.assertEqual(
            walk(systemic_graph, x),
            (
                [[SYSTEMIC_ROOT, SYSTEMIC_WORKUP, SYSTEMIC_LEFT]],
                ["Concurrent_CRT_eligible", "Concurrent_CRT_ineligible"],
            ),
        )

    def test_example_4_egfr_wt_high_pdl1_enters_right_branch(self):
        x = systemic_case("example_4_egfr_wt_high_pdl1")
        self.assertEqual(validate_data(infer_schema(systemic_graph), x), [])
        self.assertEqual(
            walk(systemic_graph, x),
            (
                [[SYSTEMIC_ROOT, SYSTEMIC_WORKUP, SYSTEMIC_RIGHT]],
                ["Concurrent_CRT_eligible", "Concurrent_CRT_ineligible"],
            ),
        )

    def test_example_5_crt_eligible_stops_at_egfr_subtype_frontier(self):
        x = systemic_case("example_5_crt_eligible_egfr_mut")
        self.assertEqual(validate_data(infer_schema(systemic_graph), x), [])
        self.assertEqual(
            walk(systemic_graph, x),
            (
                [[
                    SYSTEMIC_ROOT,
                    SYSTEMIC_WORKUP,
                    SYSTEMIC_LEFT,
                    "Concurrent_CRT_eligible",
                    SYSTEMIC_CRT,
                ]],
                [
                    "EGFR_exon_19_deletion",
                    "L858R",
                    "no_EGFR_exon_19_deletion",
                    "no_L858R",
                ],
            ),
        )

    def test_example_6_osimertinib_path_to_surveillance(self):
        x = systemic_case("example_6_osimertinib_path")
        self.assertEqual(validate_data(infer_schema(systemic_graph), x), [])
        self.assertEqual(
            walk(systemic_graph, x),
            (
                [[
                    SYSTEMIC_ROOT,
                    SYSTEMIC_WORKUP,
                    SYSTEMIC_LEFT,
                    "Concurrent_CRT_eligible",
                    SYSTEMIC_CRT,
                    "EGFR_exon_19_deletion or L858R",
                    "No_progression",
                    SYSTEMIC_OSIMERTINIB,
                    SYSTEMIC_SURVEILLANCE,
                ]],
                [],
            ),
        )

    def test_example_7_durvalumab_concurrent_to_surveillance(self):
        x = systemic_case("example_7_durvalumab_concurrent")
        self.assertEqual(validate_data(infer_schema(systemic_graph), x), [])
        self.assertEqual(
            walk(systemic_graph, x),
            (
                [[
                    SYSTEMIC_ROOT,
                    SYSTEMIC_WORKUP,
                    SYSTEMIC_RIGHT,
                    "Concurrent_CRT_eligible",
                    SYSTEMIC_CRT,
                    "No_progression",
                    DURVALUMAB_IA,
                    SYSTEMIC_SURVEILLANCE,
                ]],
                [],
            ),
        )

    def test_example_8_rt_surveillance(self):
        x = systemic_case("example_8_rt_surveillance")
        self.assertEqual(validate_data(infer_schema(systemic_graph), x), [])
        self.assertEqual(
            walk(systemic_graph, x),
            (
                [[
                    SYSTEMIC_ROOT,
                    SYSTEMIC_WORKUP,
                    SYSTEMIC_LEFT,
                    "Concurrent_CRT_ineligible",
                    "RT",
                    SYSTEMIC_SURVEILLANCE,
                ]],
                [],
            ),
        )


class ElansclcSystemicTreatmentEquivalenceTests(unittest.TestCase):
    """Tag-path walks match DOT; pdl1_percent branches intentionally diverge (lt/ge vs has tags)."""

    def _walk_labels(self, g, x):
        paths, required = walk(g, x)
        return (
            [[node.label for node in path.path] for path in paths],
            required,
        )

    def test_dot_to_graph_matches_curated_dg_on_tag_paths(self):
        dot_graph = dot_to_graph(SYSTEMIC_DOT.read_text())
        for x in SYSTEMIC_EXAMPLES:
            self.assertEqual(
                self._walk_labels(dot_graph, x),
                self._walk_labels(systemic_graph, x),
                msg=f"mismatch for {x}",
            )

    def test_curated_numeric_pdl1_diverges_from_dot_tag_conditions(self):
        dot_graph = dot_to_graph(SYSTEMIC_DOT.read_text())
        x = systemic_case("example_3_low_pdl1")
        curated_paths, curated_required = walk(systemic_graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, ["Concurrent_CRT_eligible", "Concurrent_CRT_ineligible"])
        self.assertEqual(curated_paths[0].path[-1].label, SYSTEMIC_LEFT)
        self.assertIn("EGFR_mutation", dot_required)
        self.assertIn("<1", dot_required)
        self.assertIn("pdl1_percent", dot_required)
        self.assertEqual(dot_paths[0].path[-1].label, SYSTEMIC_WORKUP)


if __name__ == "__main__":
    unittest.main()
