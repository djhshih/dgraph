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


# --- Metastatic TET ---

MET_DG = ROOT / "data/tet/dg/metastatic_curated.dg"
MET_DOT = ROOT / "data/tet/dot/metastatic.dot"
MET_BIOPSY = "Biopsy"
MET_CHEMO = "Definitive chemotherapy"
MET_FOLLOW = "Follow-up"
MET_PORT = "Postoperative radiotherapy"

met_graph = load_dg(MET_DG)
MET_PATIENTS = load_patient_cases(ROOT / "demo/patients/tet/metastatic.json")
MET_SCHEMA = infer_schema(met_graph)


def met_case(case_id: str):
    return build_patient(MET_SCHEMA, case_by_id(MET_PATIENTS, case_id))


class TetMetastaticSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(met_graph),
            {"Thymic_carcinoma": "tag", "Thymoma": "tag"},
        )


class TetMetastaticWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_histology(self):
        x = met_case("example_1_no_tags")
        self.assertEqual(validate_data(MET_SCHEMA, x), [])
        self.assertEqual(
            walk(met_graph, x),
            ([[MET_BIOPSY, MET_CHEMO]], ["Thymic_carcinoma", "Thymoma"]),
        )

    def test_example_2_carcinoma_reaches_follow_up(self):
        x = met_case("example_2_thymic_carcinoma")
        self.assertEqual(validate_data(MET_SCHEMA, x), [])
        self.assertEqual(
            walk(met_graph, x),
            ([[MET_BIOPSY, MET_CHEMO, "Thymic_carcinoma", MET_FOLLOW]], []),
        )

    def test_example_3_thymoma_takes_surgery_and_definitive_rt(self):
        x = met_case("example_3_thymoma")
        self.assertEqual(validate_data(MET_SCHEMA, x), [])
        self.assertEqual(
            walk(met_graph, x),
            (
                [
                    [MET_BIOPSY, MET_CHEMO, "Thymoma", "Surgery", MET_PORT, MET_FOLLOW],
                    [MET_BIOPSY, MET_CHEMO, "Thymoma", "Definitive_radiotherapy", MET_FOLLOW],
                ],
                [],
            ),
        )


class TetMetastaticEquivalenceTests(unittest.TestCase):
    """Histology tags match DOT; Surgery / Definitive_radiotherapy always() diverges."""

    def test_empty_patient_matches_dot(self):
        dot_graph = dot_to_graph(MET_DOT.read_text())
        x = met_case("example_1_no_tags")
        self.assertEqual(walk_labels(dot_graph, x), walk_labels(met_graph, x))

    def test_thymoma_always_diverges_from_dot_treatment_tags(self):
        dot_graph = dot_to_graph(MET_DOT.read_text())
        x = met_case("example_3_thymoma")
        curated_paths, curated_required = walk(met_graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(len(curated_paths), 2)
        self.assertEqual(dot_paths[0].path[-1].label, "Thymoma")
        self.assertIn("Surgery", dot_required)
        self.assertIn("Definitive_radiotherapy", dot_required)


# --- Resectable TET ---

RES_DG = ROOT / "data/tet/dg/resectable.dg"
RES_DOT = ROOT / "data/tet/dot/resectable.dot"
RES_ROOT = "Upfront Surgery"
RES_PORT = "Postoperative radiotherapy"
RES_CHEMO = "Postoperative chemotherapy"
RES_FOLLOW = "Follow-up"

res_graph = load_dg(RES_DG)
RES_PATIENTS = load_patient_cases(ROOT / "demo/patients/tet/resectable.json")
RES_SCHEMA = infer_schema(res_graph)


def res_case(case_id: str):
    return build_patient(RES_SCHEMA, case_by_id(RES_PATIENTS, case_id))


class TetResectableSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(res_graph),
            {
                "Thymic_carcinoma": "tag",
                "R1": "tag",
                "Masaoka-Koga_IIA": "tag",
                "Masaoka-Koga_IIB": "tag",
                "Masaoka-Koga_III": "tag",
                "Masaoka-Koga_I": "tag",
                "R0": "tag",
                "Thymoma": "tag",
                "WHO_B2": "tag",
                "WHO_B3": "tag",
                "WHO_A": "tag",
                "WHO_AB": "tag",
                "WHO_B1": "tag",
            },
        )


class TetResectableWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_histology(self):
        x = res_case("example_1_no_tags")
        self.assertEqual(validate_data(RES_SCHEMA, x), [])
        self.assertEqual(
            walk(res_graph, x),
            ([[RES_ROOT]], ["Thymic_carcinoma", "Thymoma"]),
        )

    def test_example_2_carcinoma_r1_stage_i_reaches_port(self):
        x = res_case("example_2_carcinoma_r1_stage_i")
        self.assertEqual(validate_data(RES_SCHEMA, x), [])
        self.assertEqual(
            walk(res_graph, x),
            (
                [[RES_ROOT, "Thymic_carcinoma", "R1", "Masaoka-Koga_I", RES_PORT, RES_FOLLOW]],
                [],
            ),
        )

    def test_example_3_carcinoma_r0_stage_iii_reaches_chemo_port(self):
        x = res_case("example_3_carcinoma_r0_stage_iii")
        self.assertEqual(validate_data(RES_SCHEMA, x), [])
        self.assertEqual(
            walk(res_graph, x),
            (
                [[
                    RES_ROOT,
                    "Thymic_carcinoma",
                    "R0",
                    "Masaoka-Koga_III",
                    RES_CHEMO,
                    RES_PORT,
                    RES_FOLLOW,
                ]],
                [],
            ),
        )

    def test_example_4_thymoma_r1_reaches_port(self):
        x = res_case("example_4_thymoma_r1")
        self.assertEqual(validate_data(RES_SCHEMA, x), [])
        self.assertEqual(
            walk(res_graph, x),
            ([[RES_ROOT, "Thymoma", "R1", RES_PORT, RES_FOLLOW]], []),
        )

    def test_example_5_thymoma_r0_iib_who_b2_reaches_port(self):
        x = res_case("example_5_thymoma_r0_iib_who_b2")
        self.assertEqual(validate_data(RES_SCHEMA, x), [])
        self.assertEqual(
            walk(res_graph, x),
            (
                [[
                    RES_ROOT,
                    "Thymoma",
                    "R0",
                    "Masaoka-Koga_IIB",
                    "WHO_B2 or WHO_B3",
                    RES_PORT,
                    RES_FOLLOW,
                ]],
                [],
            ),
        )

    def test_example_6_thymoma_r0_stage_i_reaches_follow_up(self):
        x = res_case("example_6_thymoma_r0_stage_i")
        self.assertEqual(validate_data(RES_SCHEMA, x), [])
        self.assertEqual(
            walk(res_graph, x),
            ([[RES_ROOT, "Thymoma", "R0", "Masaoka-Koga_I", RES_FOLLOW]], []),
        )


class TetResectableEquivalenceTests(unittest.TestCase):
    """Compiler DG matches DOT on tag paths after WHO prefix and dropped any-stage node."""

    def test_dot_to_graph_matches_dg_on_tag_paths(self):
        dot_graph = dot_to_graph(RES_DOT.read_text())
        for case_id in (
            "example_1_no_tags",
            "example_2_carcinoma_r1_stage_i",
            "example_3_carcinoma_r0_stage_iii",
            "example_4_thymoma_r1",
            "example_5_thymoma_r0_iib_who_b2",
            "example_6_thymoma_r0_stage_i",
        ):
            x = res_case(case_id)
            self.assertEqual(
                walk_labels(dot_graph, x),
                walk_labels(res_graph, x),
                msg=f"mismatch for {case_id}",
            )


# --- Unresectable TET ---

UNR_DG = ROOT / "data/tet/dg/unresectable_curated.dg"
UNR_DOT = ROOT / "data/tet/dot/unresectable.dot"
UNR_BIOPSY = "Biopsy"
UNR_PRIMARY = "Primary_chemotherapy"
UNR_CRT = "Chemoradiotherapy"
UNR_FOLLOW = "Follow-up"
UNR_PORT = "Postoperative radiotherapy"
UNR_CHEMO = "Postoperative chemotherapy"
UNR_UNRESECTABLE = (
    "Unresectable and (Masaoka-Koga_III or Masaoka-Koga_IVA) "
    "and (cTNM_IIIA or cTNM_IIIB or cTNM_IVA)"
)
UNR_RESECTABLE = (
    "Resectable and (Masaoka-Koga_III or Masaoka-Koga_IVA) "
    "and (cTNM_IIIA or cTNM_IVA)"
)
UNR_FRONTIER = [
    "Unresectable",
    "Masaoka-Koga_III",
    "Masaoka-Koga_IVA",
    "cTNM_IIIA",
    "cTNM_IIIB",
    "cTNM_IVA",
    "Resectable",
]
UNR_CRT_FOLLOW = [UNR_BIOPSY, UNR_CRT, UNR_FOLLOW]

unr_graph = load_dg(UNR_DG)
UNR_PATIENTS = load_patient_cases(ROOT / "demo/patients/tet/unresectable.json")
UNR_SCHEMA = infer_schema(unr_graph)


def unr_case(case_id: str):
    return build_patient(UNR_SCHEMA, case_by_id(UNR_PATIENTS, case_id))


class TetUnresectableSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(unr_graph),
            {
                "Unresectable": "tag",
                "Masaoka-Koga_III": "tag",
                "Masaoka-Koga_IVA": "tag",
                "cTNM_IIIA": "tag",
                "cTNM_IIIB": "tag",
                "cTNM_IVA": "tag",
                "Thymic_carcinoma": "tag",
                "Thymoma": "tag",
                "Resectable": "tag",
                "R2": "tag",
                "R0": "tag",
                "R1": "tag",
            },
        )


class TetUnresectableWalkTests(unittest.TestCase):
    def test_example_1_no_tags_crt_leaf_and_restaging_frontier(self):
        x = unr_case("example_1_no_tags")
        self.assertEqual(validate_data(UNR_SCHEMA, x), [])
        self.assertEqual(
            walk(unr_graph, x),
            (
                [[UNR_BIOPSY, UNR_PRIMARY], UNR_CRT_FOLLOW],
                UNR_FRONTIER,
            ),
        )

    def test_example_2_unresectable_carcinoma_takes_rt_and_crt(self):
        x = unr_case("example_2_unresectable_carcinoma")
        self.assertEqual(validate_data(UNR_SCHEMA, x), [])
        self.assertEqual(
            walk(unr_graph, x),
            (
                [
                    [
                        UNR_BIOPSY,
                        UNR_PRIMARY,
                        UNR_UNRESECTABLE,
                        "Thymic_carcinoma",
                        "Definitive_radiotherapy",
                        UNR_FOLLOW,
                    ],
                    [
                        UNR_BIOPSY,
                        UNR_PRIMARY,
                        UNR_UNRESECTABLE,
                        "Thymic_carcinoma",
                        UNR_CRT,
                        UNR_FOLLOW,
                    ],
                    UNR_CRT_FOLLOW,
                ],
                [],
            ),
        )

    def test_example_3_unresectable_thymoma_takes_crt_and_rt(self):
        x = unr_case("example_3_unresectable_thymoma")
        self.assertEqual(validate_data(UNR_SCHEMA, x), [])
        self.assertEqual(
            walk(unr_graph, x),
            (
                [
                    [
                        UNR_BIOPSY,
                        UNR_PRIMARY,
                        UNR_UNRESECTABLE,
                        "Thymoma",
                        UNR_CRT,
                        UNR_FOLLOW,
                    ],
                    [
                        UNR_BIOPSY,
                        UNR_PRIMARY,
                        UNR_UNRESECTABLE,
                        "Thymoma",
                        "Definitive_radiotherapy",
                        UNR_FOLLOW,
                    ],
                    UNR_CRT_FOLLOW,
                ],
                [],
            ),
        )

    def test_example_4_resectable_carcinoma_reaches_chemo_port(self):
        x = unr_case("example_4_resectable_carcinoma")
        self.assertEqual(validate_data(UNR_SCHEMA, x), [])
        self.assertEqual(
            walk(unr_graph, x),
            (
                [
                    [
                        UNR_BIOPSY,
                        UNR_PRIMARY,
                        UNR_RESECTABLE,
                        "Surgery",
                        "Thymic_carcinoma",
                        UNR_CHEMO,
                        UNR_PORT,
                        UNR_FOLLOW,
                    ],
                    UNR_CRT_FOLLOW,
                ],
                [],
            ),
        )

    def test_example_5_resectable_thymoma_r0_reaches_port(self):
        x = unr_case("example_5_resectable_thymoma_r0")
        self.assertEqual(validate_data(UNR_SCHEMA, x), [])
        self.assertEqual(
            walk(unr_graph, x),
            (
                [
                    [
                        UNR_BIOPSY,
                        UNR_PRIMARY,
                        UNR_RESECTABLE,
                        "Surgery",
                        "Thymoma",
                        "R0 or R1",
                        UNR_PORT,
                        UNR_FOLLOW,
                    ],
                    UNR_CRT_FOLLOW,
                ],
                [],
            ),
        )

    def test_example_6_resectable_thymoma_r2_reaches_chemo_port(self):
        x = unr_case("example_6_resectable_thymoma_r2")
        self.assertEqual(validate_data(UNR_SCHEMA, x), [])
        self.assertEqual(
            walk(unr_graph, x),
            (
                [
                    [
                        UNR_BIOPSY,
                        UNR_PRIMARY,
                        UNR_RESECTABLE,
                        "Surgery",
                        "Thymoma",
                        "R2",
                        UNR_CHEMO,
                        UNR_PORT,
                        UNR_FOLLOW,
                    ],
                    UNR_CRT_FOLLOW,
                ],
                [],
            ),
        )


class TetUnresectableEquivalenceTests(unittest.TestCase):
    """Treatment always() diverges from DOT has() tags."""

    def test_empty_patient_always_diverges_from_dot(self):
        dot_graph = dot_to_graph(UNR_DOT.read_text())
        x = unr_case("example_1_no_tags")
        curated_paths, curated_required = walk(unr_graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(len(curated_paths), 2)
        self.assertEqual(curated_required, UNR_FRONTIER)
        self.assertEqual(dot_paths[0].path[-1].label, UNR_BIOPSY)
        self.assertIn("Primary_chemotherapy", dot_required)
        self.assertIn("Chemoradiotherapy", dot_required)

    def test_curated_reaches_follow_up_while_dot_stops_at_biopsy(self):
        dot_graph = dot_to_graph(UNR_DOT.read_text())
        x = unr_case("example_2_unresectable_carcinoma")
        curated_paths, curated_required = walk(unr_graph, x)
        dot_paths, dot_required = walk(dot_graph, x)
        self.assertEqual(curated_required, [])
        self.assertEqual(curated_paths[0].path[-1].label, UNR_FOLLOW)
        self.assertEqual(dot_paths[0].path[-1].label, UNR_BIOPSY)
        self.assertIn("Primary_chemotherapy", dot_required)
