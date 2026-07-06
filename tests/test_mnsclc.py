import unittest
from pathlib import Path

from dgraph.dg_loader import load_dg
from dgraph.dot.interpret import dot_to_graph
from dgraph.graph import Data, walk
from dgraph.schema import infer_schema, validate_data

ROOT = Path(__file__).resolve().parents[1]
ROS1_DG = ROOT / "data/mnsclc/dg/mnsclc_ros1.dg"
ROS1_DOT = ROOT / "data/mnsclc/dot/mnsclc_ros1.dot"

ROOT_LABEL = "Stage IV mNSCLC with ROS1 translocation"
FIRST_LINE_TKIS = (
    "Crizotinib [III, A; MCBS 3; ESCAT I-B]\n"
    "Entrectinib [III, A; MCBS 3; ESCAT I-B]\n"
    "Alternative:\n"
    "Repotrectinib [III, B; ESCAT I-B]"
)
REBIOPSY = "Rebiopsy is recommended if ROS1 TKI received in first line"
LOCAL_TREATMENT = "Local treatment (surgery or RT) and continue targeted systemic treatment [IV, C]"
ALTERNATIVE = "alternative next-generation ROS1 TKIs if available [III, A] or platinum-based ChT [IV, A]"

graph = load_dg(ROS1_DG)

ROS1_EXAMPLES = [
    Data(set()),
    Data(("Oligoprogression",)),
    Data(("Systemic_progression",)),
    Data(("Oligoprogression", "no_ROS1_TKI_received_in_first_line")),
    Data(("Systemic_progression", "ROS1_TKI_received_in_first_line")),
]


class MnsclcRos1SchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(graph),
            {
                "Oligoprogression": "tag",
                "Systemic_progression": "tag",
                "no_ROS1_TKI_received_in_first_line": "tag",
                "ROS1_TKI_received_in_first_line": "tag",
            },
        )


class MnsclcRos1WalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_disease_progression(self):
        x = Data(set())
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[ROOT_LABEL, FIRST_LINE_TKIS, "Disease progression"]],
                ["Oligoprogression", "Systemic_progression"],
            ),
        )

    def test_example_2_oligoprogression_stops_at_rebiopsy(self):
        x = Data(("Oligoprogression",))
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    FIRST_LINE_TKIS,
                    "Disease progression",
                    "Oligoprogression",
                    LOCAL_TREATMENT,
                    "Systemic progression",
                    REBIOPSY,
                ]],
                ["no_ROS1_TKI_received_in_first_line", "ROS1_TKI_received_in_first_line"],
            ),
        )

    def test_example_3_systemic_progression_stops_at_rebiopsy(self):
        x = Data(("Systemic_progression",))
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    FIRST_LINE_TKIS,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY,
                ]],
                ["no_ROS1_TKI_received_in_first_line", "ROS1_TKI_received_in_first_line"],
            ),
        )

    def test_example_4_oligoprogression_no_first_line_tki(self):
        x = Data(("Oligoprogression", "no_ROS1_TKI_received_in_first_line"))
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    FIRST_LINE_TKIS,
                    "Disease progression",
                    "Oligoprogression",
                    LOCAL_TREATMENT,
                    "Systemic progression",
                    REBIOPSY,
                    "no_ROS1_TKI_received_in_first_line",
                    FIRST_LINE_TKIS,
                ]],
                [],
            ),
        )

    def test_example_5_systemic_progression_with_first_line_tki(self):
        x = Data(("Systemic_progression", "ROS1_TKI_received_in_first_line"))
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    ROOT_LABEL,
                    FIRST_LINE_TKIS,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY,
                    "ROS1_TKI_received_in_first_line",
                    ALTERNATIVE,
                ]],
                [],
            ),
        )


class MnsclcRos1EquivalenceTests(unittest.TestCase):
    def test_dot_to_graph_matches_curated_dg(self):
        graph1 = dot_to_graph(ROS1_DOT.read_text())
        graph2 = load_dg(ROS1_DG)
        self.assertEqual(infer_schema(graph1), infer_schema(graph2))
        for x in ROS1_EXAMPLES:
            self.assertEqual(walk(graph1, x), walk(graph2, x))


if __name__ == "__main__":
    unittest.main()
