import unittest
from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.dot.interpret import dot_to_graph
from dgraph.graph import walk
from dgraph.patient_data import build_patient, case_by_id, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[1]


def walk_labels(graph, x):
    paths, required = walk(graph, x)
    return [[node.label for node in path.path] for path in paths], required


# --- Locoregional NPC ---

LOC_DG = ROOT / "data/npc/dg/locoregional_curated.dg"
LOC_DOT = ROOT / "data/npc/dot/locoregional.dot"

LOC_ROOT = "Locoregional NPC"
IMRT_IIA = "IMRT [II, A]"
IMRT_CHT_IIB = "IMRT-ChT [II, B]"
IMRT_CHT_IA = "IMRT-ChT [I, A]"
ICT_IA = "ICT + IMRT-ChT [I, A]"
AC_IB = "IMRT-ChT + AC [I, B]"
T0_N2_M0 = "(T0 or T1 or T2) and N2 and M0"
T3_N0_M0 = "T3 and N0 and M0"
N3_M0 = "N3 and M0"
LOC_STAGE_FRONTIER = ["Stage_I", "Stage_II", "Stage_III", "Stage_IVA"]
LOC_SCHEMA_DICT = {
    "Stage_I": "tag",
    "Stage_II": "tag",
    "Stage_III": "tag",
    "T0": "tag",
    "T1": "tag",
    "T2": "tag",
    "N2": "tag",
    "M0": "tag",
    "T3": "tag",
    "N0": "tag",
    "N1": "tag",
    "Stage_IVA": "tag",
    "T4": "tag",
    "N3": "tag",
}

loc_graph = load_dg(LOC_DG)
LOC_PATIENTS = load_patient_cases(ROOT / "demo/patients/npc/locoregional.json")
LOC_SCHEMA = infer_schema(loc_graph)


def loc_case(case_id: str):
    return build_patient(LOC_SCHEMA, case_by_id(LOC_PATIENTS, case_id))


LOC_EXAMPLES = [
    loc_case("example_1_no_tags"),
    loc_case("example_2_stage_i"),
    loc_case("example_3_stage_ii"),
    loc_case("example_4_stage_iii_t3_n0_m0"),
    loc_case("example_5_stage_iii_t0_n2_m0"),
    loc_case("example_6_stage_iva_n3_m0"),
]


class NpcLocoregionalSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(infer_schema(loc_graph), LOC_SCHEMA_DICT)


class NpcLocoregionalWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_stage_frontier(self):
        x = loc_case("example_1_no_tags")
        self.assertEqual(validate_data(LOC_SCHEMA, x), [])
        self.assertEqual(
            walk(loc_graph, x),
            ([[LOC_ROOT]], LOC_STAGE_FRONTIER),
        )

    def test_example_2_stage_i_reaches_imrt(self):
        x = loc_case("example_2_stage_i")
        self.assertEqual(validate_data(LOC_SCHEMA, x), [])
        self.assertEqual(
            walk(loc_graph, x),
            ([[LOC_ROOT, "Stage_I", IMRT_IIA]], []),
        )

    def test_example_3_stage_ii_takes_both_treatment_options(self):
        x = loc_case("example_3_stage_ii")
        self.assertEqual(validate_data(LOC_SCHEMA, x), [])
        self.assertEqual(
            walk(loc_graph, x),
            (
                [
                    [LOC_ROOT, "Stage_II", IMRT_IIA],
                    [LOC_ROOT, "Stage_II", IMRT_CHT_IIB],
                ],
                [],
            ),
        )

    def test_example_4_t3_n0_m0_reaches_imrt_cht(self):
        x = loc_case("example_4_stage_iii_t3_n0_m0")
        self.assertEqual(validate_data(LOC_SCHEMA, x), [])
        self.assertEqual(
            walk(loc_graph, x),
            ([[LOC_ROOT, "Stage_III", T3_N0_M0, IMRT_CHT_IA]], []),
        )

    def test_example_5_t0_n2_m0_reaches_three_stage_iii_options(self):
        x = loc_case("example_5_stage_iii_t0_n2_m0")
        self.assertEqual(validate_data(LOC_SCHEMA, x), [])
        self.assertEqual(
            walk(loc_graph, x),
            (
                [
                    [LOC_ROOT, "Stage_III", T0_N2_M0, IMRT_CHT_IA],
                    [LOC_ROOT, "Stage_III", T0_N2_M0, ICT_IA],
                    [LOC_ROOT, "Stage_III", T0_N2_M0, AC_IB],
                ],
                [],
            ),
        )

    def test_example_6_n3_m0_reaches_two_stage_iva_options(self):
        x = loc_case("example_6_stage_iva_n3_m0")
        self.assertEqual(validate_data(LOC_SCHEMA, x), [])
        self.assertEqual(
            walk(loc_graph, x),
            (
                [
                    [LOC_ROOT, "Stage_IVA", N3_M0, ICT_IA],
                    [LOC_ROOT, "Stage_IVA", N3_M0, AC_IB],
                ],
                [],
            ),
        )


class NpcLocoregionalEquivalenceTests(unittest.TestCase):
    """Flattened all_of/any_of in curated `.dg` still matches DOT walks."""

    def test_dot_to_graph_matches_dg(self):
        dot_graph = dot_to_graph(LOC_DOT.read_text())
        for x in LOC_EXAMPLES:
            self.assertEqual(
                walk_labels(dot_graph, x),
                walk_labels(loc_graph, x),
                msg=f"mismatch for {x}",
            )


# --- Recurrent or metastatic NPC ---

REC_DG = ROOT / "data/npc/dg/recurrent_metastatic.dg"
REC_DOT = ROOT / "data/npc/dot/recurrent_metastatic.dot"

REC_ROOT = "Recurrent or metastatic NPC"
LOCAL = "Local_or_regional_recurrence"
MET = "Metastatic_disease"
AMENABLE = "Amenable_to_salvage_surgery_or_re-irradiation"
NOT_AMENABLE = "Not_amenable_to_salvage_surgery_or_re-irradiation"
NEWLY = "Newly_diagnosed"
NOT_NEWLY = "Not_newly_diagnosed"
SURGERY = "Surgery +/- IMRT or IMRT +/- ChT [III, A]"
NEWLY_TX = "First line:\nChT followed by RT on T and N sites [II, A]"
FIRST = (
    "First line:\n"
    "Gemcitabine-cisplatin [I, A]\n"
    "Camrelizumab-gemcitabine-cisplatin [II, A; MCBS 3]\n"
    "Toripalimab-gemcitabine-cisplatin [II, A; MCBS 3]"
)
SECOND = (
    "Second line:\n"
    "Nivolumab, pembrolizumab, camrelizumab [III, B];\n"
    "ChT (paclitaxel, docetaxel, 5-FU, capecitabine, irinotecan, "
    "vinorelbine, ifosfamide, doxorubicin, oxaliplatin, cetuximab) [III-IV, B]"
)

rec_graph = load_dg(REC_DG)
REC_PATIENTS = load_patient_cases(
    ROOT / "demo/patients/npc/recurrent_metastatic.json"
)
REC_SCHEMA = infer_schema(rec_graph)


def rec_case(case_id: str):
    return build_patient(REC_SCHEMA, case_by_id(REC_PATIENTS, case_id))


REC_EXAMPLES = [
    rec_case("example_1_no_tags"),
    rec_case("example_2_local_amenable"),
    rec_case("example_3_local_salvage"),
    rec_case("example_4_local_systemic"),
    rec_case("example_5_metastatic_newly_diagnosed"),
    rec_case("example_6_metastatic_not_newly_diagnosed"),
]


class NpcRecurrentMetastaticSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(rec_graph),
            {
                "Local_or_regional_recurrence": "tag",
                "Amenable_to_salvage_surgery_or_re-irradiation": "tag",
                "Not_amenable_to_salvage_surgery_or_re-irradiation": "tag",
                "Metastatic_disease": "tag",
                "Newly_diagnosed": "tag",
                "Not_newly_diagnosed": "tag",
            },
        )


class NpcRecurrentMetastaticWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_presentation_frontier(self):
        x = rec_case("example_1_no_tags")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT]], [LOCAL, MET]),
        )

    def test_example_2_local_stops_at_salvage_frontier(self):
        x = rec_case("example_2_local_amenable")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, LOCAL]], [AMENABLE, NOT_AMENABLE]),
        )

    def test_example_3_local_salvage_reaches_surgery(self):
        x = rec_case("example_3_local_salvage")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, LOCAL, AMENABLE, SURGERY]], []),
        )

    def test_example_4_local_not_amenable_reaches_second_line(self):
        x = rec_case("example_4_local_systemic")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, LOCAL, NOT_AMENABLE, FIRST, SECOND]], []),
        )

    def test_example_5_newly_diagnosed_reaches_cht_rt(self):
        x = rec_case("example_5_metastatic_newly_diagnosed")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, MET, NEWLY, NEWLY_TX]], []),
        )

    def test_example_6_not_newly_diagnosed_reaches_shared_systemic(self):
        x = rec_case("example_6_metastatic_not_newly_diagnosed")
        self.assertEqual(validate_data(REC_SCHEMA, x), [])
        self.assertEqual(
            walk(rec_graph, x),
            ([[REC_ROOT, MET, NOT_NEWLY, FIRST, SECOND]], []),
        )


class NpcRecurrentMetastaticEquivalenceTests(unittest.TestCase):
    def test_dot_to_graph_matches_dg(self):
        dot_graph = dot_to_graph(REC_DOT.read_text())
        for x in REC_EXAMPLES:
            self.assertEqual(
                walk_labels(dot_graph, x),
                walk_labels(rec_graph, x),
                msg=f"mismatch for {x}",
            )


# --- Follow-up of NPC ---

FU_DG = ROOT / "data/npc/dg/follow_up_curated.dg"
FU_DOT = ROOT / "data/npc/dot/follow_up.dot"

FU_ROOT = "Follow-up"
IMAGING = "Imaging"
IMAGING_TX = (
    "Three months after IMRT, then every 6 months up to the 3rd year "
    "(for T2-T4 diseases) [V, B]\nMRI [II, B]\nPET (higher specificity) [II, B]"
)
NASAL = "Nasal examination"
NASAL_TX = (
    "Endoscopic assessment every 3 months in the first year, every 6 months "
    "in the second and third years and annually thereafter for the first 5 years [V, B]"
)
EBV = "Plasma EBV DNA"
EBV_TX = "One to four weeks after IMRT [II, B] then every year [V, B]"
THYROID = "Thyroid and pituitary assessment"
THYROID_TX = (
    "Thyroid function assessment every year [V, B]\n"
    "Pituitary function assessment in case of signs/symptoms [V, B]"
)
FU_PATHS = [
    [FU_ROOT, IMAGING, IMAGING_TX],
    [FU_ROOT, NASAL, NASAL_TX],
    [FU_ROOT, EBV, EBV_TX],
    [FU_ROOT, THYROID, THYROID_TX],
]

fu_graph = load_dg(FU_DG)
FU_PATIENTS = load_patient_cases(ROOT / "demo/patients/npc/follow_up.json")
FU_SCHEMA = infer_schema(fu_graph)


def fu_case(case_id: str):
    return build_patient(FU_SCHEMA, case_by_id(FU_PATIENTS, case_id))


FU_EXAMPLES = [
    fu_case("example_1_no_tags"),
    fu_case("example_2_unrelated_tags"),
]


class NpcFollowUpSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(infer_schema(fu_graph), {})


class NpcFollowUpWalkTests(unittest.TestCase):
    def test_example_1_no_tags_reaches_all_four_schedules(self):
        x = fu_case("example_1_no_tags")
        self.assertEqual(validate_data(FU_SCHEMA, x), [])
        self.assertEqual(walk(fu_graph, x), (FU_PATHS, []))

    def test_example_2_unrelated_tags_do_not_change_walk(self):
        x = fu_case("example_2_unrelated_tags")
        self.assertEqual(validate_data(FU_SCHEMA, x), [])
        self.assertEqual(walk(fu_graph, x), (FU_PATHS, []))


class NpcFollowUpEquivalenceTests(unittest.TestCase):
    """Curated title `Follow-up` replaces the compiler synthetic `root`."""

    def test_curated_title_diverges_from_synthetic_root(self):
        dot_graph = dot_to_graph(FU_DOT.read_text())
        x = fu_case("example_1_no_tags")
        dot_paths, dot_required = walk_labels(dot_graph, x)
        curated_paths, curated_required = walk_labels(fu_graph, x)
        self.assertEqual(dot_required, curated_required)
        self.assertEqual(dot_graph.label, "root")
        self.assertEqual(fu_graph.label, FU_ROOT)
        self.assertEqual(
            [[FU_ROOT] + path[1:] for path in dot_paths],
            curated_paths,
        )
