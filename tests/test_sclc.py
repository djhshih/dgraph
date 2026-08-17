import unittest
from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.dot.interpret import dot_to_graph
from dgraph.graph import walk
from dgraph.patient_data import build_patient, case_by_id, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[1]
DG = ROOT / "data/sclc/dg/extensive_stage_curated.dg"
DOT = ROOT / "data/sclc/dot/extensive_stage.dot"

ROOT_LABEL = (
    "Extensive-stage SCLC (i.e. stage IV or stage III SCLC not eligible "
    "for treatment of curative intent)"
)
IO_TX = (
    "Carboplatin-etoposide-atezolizumab (4 cycles) and maintenance atezolizumab [I, A; MCBS 3]\n"
    "Platinum-etoposide-durvalumab (4 cycles) and maintenance durvalumab [I, A; MCBS 3]"
)
CONTRA_TX = (
    "Carboplatin-etoposide 4-6 cycles [I, A]\n"
    "Carboplatin-oral topotecan [II, C]\n"
    "Cisplatin-irinotecan [II, C]"
)
SCLC_TX = (
    "Carboplatin-etoposide 4-6 cycles [I, A]\n"
    "Carboplatin-gemcitabine 4-6 cycles [II, C]"
)
PS01_NO_IO = ">= 0 PS and <= 1 PS and No_contraindication_for_IO"
PS01_CONTRA = ">= 0 PS and <= 1 PS and Contraindications_for_IO"
PS2_SCLC = ">= 2 PS and due_to_SCLC"
PS2_COMORB = ">= 2 PS and due_to_comorbidities"
RESPONSE = "Response and >= 0 PS_after_response and <= 2 PS_after_response"
CONSOLIDATION = "Consolidation thoracic RT is an option [II, C]"
AGE = "< 75 Age"
PCI = "PCI [II, B] or MRI surveillance [II, B]"
PS_FRONTIER = [
    "PS",
    "No_contraindication_for_IO",
    "Contraindications_for_IO",
    "due_to_SCLC",
    "due_to_comorbidities",
]
CONTRA_LEAF = [
    ROOT_LABEL,
    PS01_CONTRA,
    CONTRA_TX,
    RESPONSE,
    CONSOLIDATION,
    AGE,
    PCI,
]
SCLC_LEAF = [
    ROOT_LABEL,
    PS2_SCLC,
    SCLC_TX,
    RESPONSE,
    CONSOLIDATION,
    AGE,
    PCI,
]

graph = load_dg(DG)
PATIENTS = load_patient_cases(ROOT / "demo/patients/sclc/extensive_stage.json")
SCHEMA = infer_schema(graph)


def case(case_id: str):
    return build_patient(SCHEMA, case_by_id(PATIENTS, case_id))


EXAMPLES = [
    case("example_1_no_tags"),
    case("example_2_ps1_io_eligible"),
    case("example_3_ps1_io_contraindicated"),
    case("example_4_ps1_contra_response_under_75"),
    case("example_5_ps3_due_to_sclc_response_under_75"),
    case("example_6_ps3_due_to_comorbidities"),
]


class SclcExtensiveStageSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(graph),
            {
                "PS": "unknown",
                "No_contraindication_for_IO": "tag",
                "Contraindications_for_IO": "tag",
                "Response": "tag",
                "PS_after_response": "unknown",
                "Age": "unknown",
                "due_to_SCLC": "tag",
                "due_to_comorbidities": "tag",
            },
        )


class SclcExtensiveStageWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_ps_frontier(self):
        x = case("example_1_no_tags")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            ([[ROOT_LABEL]], PS_FRONTIER),
        )

    def test_example_2_ps1_io_eligible_reaches_chemo_io_leaf(self):
        x = case("example_2_ps1_io_eligible")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            ([[ROOT_LABEL, PS01_NO_IO, IO_TX]], []),
        )

    def test_example_3_ps1_io_contraindicated_stops_at_response(self):
        x = case("example_3_ps1_io_contraindicated")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            ([[ROOT_LABEL, PS01_CONTRA, CONTRA_TX]], ["Response", "PS_after_response"]),
        )

    def test_example_4_ps1_contra_response_under_75_reaches_pci(self):
        x = case("example_4_ps1_contra_response_under_75")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(walk(graph, x), ([CONTRA_LEAF], []))

    def test_example_5_ps3_due_to_sclc_response_under_75_reaches_pci(self):
        x = case("example_5_ps3_due_to_sclc_response_under_75")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(walk(graph, x), ([SCLC_LEAF], []))

    def test_example_6_ps3_due_to_comorbidities_reaches_bsc(self):
        x = case("example_6_ps3_due_to_comorbidities")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            ([[ROOT_LABEL, PS2_COMORB, "BSC"]], []),
        )


class SclcExtensiveStageEquivalenceTests(unittest.TestCase):
    """Numeric PS/Age and Response/Age branches diverge from DOT tag-soup compile."""

    def test_curated_numeric_ps_diverges_from_dot_tag_conditions(self):
        dot_graph = dot_to_graph(DOT.read_text())
        x = case("example_2_ps1_io_eligible")
        curated_paths, curated_required = walk(graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, IO_TX)
        self.assertEqual(dot_paths[0].path[-1].label, ROOT_LABEL)
        self.assertIn(">=0", dot_required)
        self.assertIn("PS", dot_required)

    def test_curated_response_age_branches_diverge_from_dot_chain(self):
        dot_graph = dot_to_graph(DOT.read_text())
        x = case("example_4_ps1_contra_response_under_75")
        curated_paths, curated_required = walk(graph, x)
        dot_paths, _dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, PCI)
        self.assertEqual(dot_paths[0].path[-1].label, ROOT_LABEL)


# --- Limited-stage SCLC ---

LS_DG = ROOT / "data/sclc/dg/limited_stage_curated.dg"
LS_DOT = ROOT / "data/sclc/dot/limited_stage.dot"

LS_ROOT = (
    "Limited-stage SCLC (i.e. stage I-III SCLC eligible for treatment of curative intent)"
)
LS_SURGERY = "Surgical resection [III, B]"
LS_ADJUVANT = "Adjuvant cisplatin-etoposide (4 cycles) [IV, A]"
LS_CRT_IV = "Concurrent CRT [IV, A]"
LS_CRT_I = "Concurrent CRT [I, A]"
LS_SEQ = "Sequential CRT [V, B]"
LS_PCI_IA = "PCI [I, A]"
LS_STAGE_I_II = "Stage_I-II and (cT1 or cT2) and N0"
LS_STAGE_I_III = "Stage_I-III and (cT1 or cT2 or cT3 or cT4) and (N0 or N1 or N2 or N3) and M0"
LS_PT = "(pT1 or pT2) and (N0 or N1) and R0"
LS_STAGE_FRONTIER = [
    "Stage_I-II",
    "cT1",
    "cT2",
    "N0",
    "Stage_I-III",
    "cT3",
    "cT4",
    "N1",
    "N2",
    "N3",
    "M0",
]
LS_POSTOP_FRONTIER = [
    "pT1",
    "pT2",
    "N0",
    "N1",
    "R0",
    "N2",
    "R1",
    "R2",
]

ls_graph = load_dg(LS_DG)
LS_PATIENTS = load_patient_cases(ROOT / "demo/patients/sclc/limited_stage.json")
LS_SCHEMA = infer_schema(ls_graph)


def ls_case(case_id: str):
    return build_patient(LS_SCHEMA, case_by_id(LS_PATIENTS, case_id))


class SclcLimitedStageSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(ls_graph),
            {
                "Stage_I-II": "tag",
                "cT1": "tag",
                "cT2": "tag",
                "N0": "tag",
                "pT1": "tag",
                "pT2": "tag",
                "N1": "tag",
                "R0": "tag",
                "N2": "tag",
                "R1": "tag",
                "R2": "tag",
                "No_progression": "tag",
                "PS": "unknown",
                "Age": "unknown",
                "Frail": "tag",
                "Stage_I-III": "tag",
                "cT3": "tag",
                "cT4": "tag",
                "N3": "tag",
                "M0": "tag",
            },
        )


class SclcLimitedStageWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_stage_frontier(self):
        x = ls_case("example_1_no_tags")
        self.assertEqual(validate_data(LS_SCHEMA, x), [])
        self.assertEqual(
            walk(ls_graph, x),
            ([[LS_ROOT]], LS_STAGE_FRONTIER),
        )

    def test_example_2_stage_i_ii_stops_at_postop_frontier(self):
        x = ls_case("example_2_stage_i_ii_surgery_frontier")
        self.assertEqual(validate_data(LS_SCHEMA, x), [])
        self.assertEqual(
            walk(ls_graph, x),
            (
                [[LS_ROOT, LS_STAGE_I_II, LS_SURGERY]],
                LS_POSTOP_FRONTIER,
            ),
        )

    def test_example_3_adjuvant_r0_reaches_leaf(self):
        x = ls_case("example_3_adjuvant_r0")
        self.assertEqual(validate_data(LS_SCHEMA, x), [])
        self.assertEqual(
            walk(ls_graph, x),
            (
                [[
                    LS_ROOT,
                    LS_STAGE_I_II,
                    LS_SURGERY,
                    LS_PT,
                    LS_ADJUVANT,
                ]],
                [],
            ),
        )

    def test_example_4_n2_concurrent_crt_reaches_pci(self):
        x = ls_case("example_4_n2_concurrent_crt_pci")
        self.assertEqual(validate_data(LS_SCHEMA, x), [])
        self.assertEqual(
            walk(ls_graph, x),
            (
                [[
                    LS_ROOT,
                    LS_STAGE_I_II,
                    LS_SURGERY,
                    "N2 or R1 or R2",
                    LS_CRT_IV,
                    "No_progression",
                    ">= 0 PS and <= 1 PS and <= 70 Age",
                    LS_PCI_IA,
                ]],
                [],
            ),
        )

    def test_example_5_stage_iii_ps_0_1_reaches_pci(self):
        x = ls_case("example_5_stage_iii_ps_0_1_pci")
        self.assertEqual(validate_data(LS_SCHEMA, x), [])
        self.assertEqual(
            walk(ls_graph, x),
            (
                [[
                    LS_ROOT,
                    LS_STAGE_I_III,
                    ">= 0 PS and <= 1 PS",
                    LS_CRT_I,
                    "No_progression",
                    ">= 0 PS and <= 1 PS and <= 70 Age",
                    LS_PCI_IA,
                ]],
                [],
            ),
        )

    def test_example_6_stage_iii_ps_ge2_frail_shared_pci(self):
        x = ls_case("example_6_stage_iii_ps_ge2_frail")
        self.assertEqual(validate_data(LS_SCHEMA, x), [])
        self.assertEqual(
            walk(ls_graph, x),
            (
                [[
                    LS_ROOT,
                    LS_STAGE_I_III,
                    ">= 2 PS",
                    LS_SEQ,
                    "No_progression",
                    "> 70 Age or Frail",
                    "Shared decision making for PCI [V, C]",
                ]],
                [],
            ),
        )


class SclcLimitedStageEquivalenceTests(unittest.TestCase):
    """T/N tag paths match DOT; numeric PS/Age and No_progression still diverge."""

    def test_dot_to_graph_matches_curated_dg_on_tag_paths(self):
        dot_graph = dot_to_graph(LS_DOT.read_text())
        for case_id in (
            "example_1_no_tags",
            "example_2_stage_i_ii_surgery_frontier",
            "example_3_adjuvant_r0",
        ):
            x = ls_case(case_id)
            dot_paths, dot_required = walk(dot_graph, x)
            curated_paths, curated_required = walk(ls_graph, x)
            self.assertEqual(
                [[node.label for node in path.path] for path in dot_paths],
                [[node.label for node in path.path] for path in curated_paths],
                msg=f"paths mismatch for {case_id}",
            )
            self.assertEqual(dot_required, curated_required, msg=f"required mismatch for {case_id}")

    def test_curated_numeric_ps_age_diverges_from_dot_tag_conditions(self):
        dot_graph = dot_to_graph(LS_DOT.read_text())
        x = ls_case("example_5_stage_iii_ps_0_1_pci")
        curated_paths, curated_required = walk(ls_graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, LS_PCI_IA)
        self.assertEqual(dot_paths[0].path[-1].label, LS_STAGE_I_III)
        self.assertIn(">=0", dot_required)
        self.assertIn("PS", dot_required)


# --- Recurrent SCLC ---

REC_DG = ROOT / "data/sclc/dg/recurrent_curated.dg"
REC_DOT = ROOT / "data/sclc/dot/recurrent.dot"

REC_ROOT = "Recurrent SCLC (i.e. second-line therapy and beyond)"
REC_TFI_LT3 = "< 3 TFI"
REC_TFI_GE3 = ">= 3 TFI"
REC_REFRACTORY = "Refractory or > 2 PS"
REC_PS_0_2 = ">= 0 PS and <= 2 PS"
REC_BSC = "BSC [II, C]\nLurbinectedin [III, C; MCBS 1]"
REC_PS02_TX = (
    "Oral or i.v. topotecan [I, A]\n"
    "Cyclophosphamide-doxorubicin-vincristine [II, B]\n"
    "Lurbinectedin [III, C; MCBS 1]"
)
REC_RECHALLENGE = (
    "Rechallenge with platinum-etoposide [II, B]\n"
    "Oral or i.v. topotecan [I, A]\n"
    "Cyclophosphamide-doxorubicin-vincristine [II, B]"
)

rec_graph = load_dg(REC_DG)
REC_PATIENTS = load_patient_cases(ROOT / "demo/patients/sclc/recurrent.json")
REC_SCHEMA = infer_schema(rec_graph)


def rec_case(case_id: str):
    return build_patient(REC_SCHEMA, case_by_id(REC_PATIENTS, case_id))


class SclcRecurrentSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(rec_graph),
            {
                "TFI": "unknown",
                "Refractory": "tag",
                "PS": "unknown",
            },
        )


class SclcRecurrentWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_tfi_frontier(self):
        x = rec_case("example_1_no_tags")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT]], ["TFI"]),
        )

    def test_example_2_tfi_lt_3_stops_at_ps_frontier(self):
        x = rec_case("example_2_tfi_lt_3")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, REC_TFI_LT3]], ["Refractory", "PS"]),
        )

    def test_example_3_resistant_ps_gt_2_reaches_bsc(self):
        x = rec_case("example_3_resistant_ps_gt_2")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, REC_TFI_LT3, REC_REFRACTORY, REC_BSC]], []),
        )

    def test_example_4_resistant_ps_0_2_reaches_topotecan(self):
        x = rec_case("example_4_resistant_ps_0_2")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, REC_TFI_LT3, REC_PS_0_2, REC_PS02_TX]], []),
        )

    def test_example_5_resistant_refractory_reaches_bsc(self):
        x = rec_case("example_5_resistant_refractory")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, REC_TFI_LT3, REC_REFRACTORY, REC_BSC]], []),
        )

    def test_example_6_sensitive_reaches_shared_ps02_list(self):
        x = rec_case("example_6_sensitive_rechallenge")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, REC_TFI_GE3, REC_RECHALLENGE, REC_PS02_TX]], []),
        )


class SclcRecurrentEquivalenceTests(unittest.TestCase):
    """Numeric TFI/PS diverge from DOT tag-soup compile."""

    def test_empty_patient_paths_match_required_diverges(self):
        dot_graph = dot_to_graph(REC_DOT.read_text())
        x = rec_case("example_1_no_tags")
        dot_paths, dot_required = walk(dot_graph, x)
        curated_paths, curated_required = walk(rec_graph, x)
        self.assertEqual(
            [[node.label for node in path.path] for path in dot_paths],
            [[node.label for node in path.path] for path in curated_paths],
        )
        self.assertEqual(curated_required, ["TFI"])
        self.assertIn("<3", dot_required)
        self.assertIn("TFI", dot_required)
        self.assertIn(">=3", dot_required)

    def test_curated_numeric_tfi_ps_diverges_from_dot_tag_conditions(self):
        dot_graph = dot_to_graph(REC_DOT.read_text())
        x = rec_case("example_4_resistant_ps_0_2")
        curated_paths, curated_required = walk(rec_graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, REC_PS02_TX)
        self.assertEqual(dot_paths[0].path[-1].label, REC_ROOT)
        self.assertIn("<3", dot_required)
        self.assertIn("TFI", dot_required)

