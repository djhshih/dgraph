import unittest
from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.dot.interpret import dot_to_graph
from dgraph.graph import walk
from dgraph.patient_data import build_patient, case_by_id, load_patient_cases
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[1]
DG = ROOT / "data/mpm/dg/inoperable_curated.dg"
DOT = ROOT / "data/mpm/dot/inoperable.dot"

ROOT_LABEL = "MPM unsuitable for multimodality treatment (e.g. PS 0-1)"
NIVO_IPI = "Nivolumab-ipilimumab (up to 2 years equivalent dosing) [I, A; MCBS 3]"
THIRD_LINE_NIVO = "Nivolumab [I, A]\nNivolumab-ipilimumab [II, C]"
BSC = "Best supportive care"

graph = load_dg(DG)
PATIENTS = load_patient_cases(ROOT / "fixtures/patients/mpm/inoperable.json")
SCHEMA = infer_schema(graph)


def case(case_id: str):
    return build_patient(SCHEMA, case_by_id(PATIENTS, case_id))


class MpmInoperableSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(infer_schema(graph), {"PS": "unknown"})


class MpmInoperableWalkTests(unittest.TestCase):
    def test_example_1_no_ps_stops_at_ps_frontier(self):
        x = case("example_1_no_ps")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            ([[ROOT_LABEL]], ["PS"]),
        )

    def test_example_2_ps0_reaches_third_line_nivo_via_many_optional_paths(self):
        x = case("example_2_ps0")
        self.assertEqual(validate_data(SCHEMA, x), [])
        paths, required = walk(graph, x)
        self.assertEqual(required, [])
        self.assertEqual(len(paths), 24)
        self.assertTrue(all(p.path[-1].label == THIRD_LINE_NIVO for p in paths))
        # Both first-line arms are available for PS 0.
        first_arms = {p.path[1].label for p in paths}
        self.assertEqual(first_arms, {">= 0 PS <= 1 PS", ">= 0 PS <= 2 PS"})
        self.assertTrue(any(NIVO_IPI in [n.label for n in p.path] for p in paths))

    def test_example_3_ps2_chemo_then_bsc(self):
        x = case("example_3_ps2")
        self.assertEqual(validate_data(SCHEMA, x), [])
        paths, required = walk(graph, x)
        self.assertEqual(required, [])
        self.assertEqual(len(paths), 4)
        self.assertTrue(all(p.path[1].label == ">= 0 PS <= 2 PS" for p in paths))
        self.assertTrue(all(p.path[-1].label == BSC for p in paths))

    def test_example_4_ps3_best_supportive_care(self):
        x = case("example_4_ps3")
        self.assertEqual(validate_data(SCHEMA, x), [])
        self.assertEqual(
            walk(graph, x),
            ([[ROOT_LABEL, ">= 3 PS", BSC]], []),
        )

    def test_example_5_ps1_matches_ps0_path_count(self):
        x = case("example_5_ps1")
        self.assertEqual(validate_data(SCHEMA, x), [])
        paths, required = walk(graph, x)
        self.assertEqual(required, [])
        self.assertEqual(len(paths), 24)
        self.assertTrue(all(p.path[-1].label == THIRD_LINE_NIVO for p in paths))