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

### --------------------------------------------- BRAF ---------------------------------------------
BRAF_DG = ROOT / "data/mnsclc/dg/mnsclc_braf.dg"
BRAF_DOT = ROOT / "data/mnsclc/dot/mnsclc_braf.dot"

BRAF_ROOT_LABEL = "Stage IV mNSCLC with BRAF V600 mutation"
FIRST_LINE = "Dabrafenib-trametinib [III, A; MCBS 2; ESCAT I-B]"
PLATINUM = "platinum-based ChT +/- immunotherapy [IV, A]"
IMMUNOTHERAPY = (
    "immunotherapy +/- platinum-based ChT [IV, B]\n"
    "Dabrafenib-trametinib if not received in first line [III, A; MCBS 2; ESCAT I-B]"
)

braf_graph = load_dg(BRAF_DG)

BRAF_EXAMPLES = [
    Data(set()),
    Data(("Oligoprogression",)),
    Data(("Systemic_progression",)),
    Data(("Oligoprogression", "no_smoking_history")),
    Data(("Systemic_progression", "smoking_history")),
]


class MnsclcBrafSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(braf_graph),
            {
                "Oligoprogression": "tag",
                "Systemic_progression": "tag",
                "no_smoking_history": "tag",
                "smoking_history": "tag",
            },
        )


class MnsclcBrafWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_disease_progression(self):
        x = Data(set())
        self.assertEqual(validate_data(infer_schema(braf_graph), x), [])
        self.assertEqual(
            walk(braf_graph, x),
            (
                [[BRAF_ROOT_LABEL, FIRST_LINE, "Disease_progression"]],
                ["Oligoprogression", "Systemic_progression"],
            ),
        )

    def test_example_2_oligoprogression_stops_at_smoking_history_fork(self):
        x = Data(("Oligoprogression",))
        self.assertEqual(validate_data(infer_schema(braf_graph), x), [])
        self.assertEqual(
            walk(braf_graph, x),
            (
                [[
                    BRAF_ROOT_LABEL,
                    FIRST_LINE,
                    "Disease_progression",
                    "Oligoprogression",
                    LOCAL_TREATMENT,
                    "Systemic_progression",
                ]],
                ["no_smoking_history", "smoking_history"],
            ),
        )

    def test_example_3_systemic_progression_stops_at_smoking_history_fork(self):
        x = Data(("Systemic_progression",))
        self.assertEqual(validate_data(infer_schema(braf_graph), x), [])
        self.assertEqual(
            walk(braf_graph, x),
            (
                [[
                    BRAF_ROOT_LABEL,
                    FIRST_LINE,
                    "Disease_progression",
                    "Systemic_progression",
                ]],
                ["no_smoking_history", "smoking_history"],
            ),
        )

    def test_example_4_oligoprogression_no_smoking_history(self):
        x = Data(("Oligoprogression", "no_smoking_history"))
        self.assertEqual(validate_data(infer_schema(braf_graph), x), [])
        self.assertEqual(
            walk(braf_graph, x),
            (
                [[
                    BRAF_ROOT_LABEL,
                    FIRST_LINE,
                    "Disease_progression",
                    "Oligoprogression",
                    LOCAL_TREATMENT,
                    "Systemic_progression",
                    "no_smoking_history",
                    PLATINUM,
                ]],
                [],
            ),
        )

    def test_example_5_systemic_progression_smoking_history(self):
        x = Data(("Systemic_progression", "smoking_history"))
        self.assertEqual(validate_data(infer_schema(braf_graph), x), [])
        self.assertEqual(
            walk(braf_graph, x),
            (
                [[
                    BRAF_ROOT_LABEL,
                    FIRST_LINE,
                    "Disease_progression",
                    "Systemic_progression",
                    "smoking_history",
                    IMMUNOTHERAPY,
                ]],
                [],
            ),
        )


class MnsclcBrafEquivalenceTests(unittest.TestCase):
    def test_dot_to_graph_matches_curated_dg(self):
        graph1 = dot_to_graph(BRAF_DOT.read_text())
        graph2 = load_dg(BRAF_DG)
        self.assertEqual(infer_schema(graph1), infer_schema(graph2))
        for x in BRAF_EXAMPLES:
            self.assertEqual(walk(graph1, x), walk(graph2, x))

### --------------------------------------------- ALK ---------------------------------------------
ALK_DG = ROOT / "data/mnsclc/dg/mnsclc_alk.dg"
ALK_DOT = ROOT / "data/mnsclc/dot/mnsclc_alk.dot"

ALK_ROOT_LABEL = "Stage IV mNSCLC with ALK translocation"
FIRST_LINE_ALK = (
    "Alectinib [I, A; MCBS 4; ESCAT I-A]\n"
    "Brigatinib [I, A; MCBS 4; ESCAT I-A]\n"
    "Lorlatinib [I, A; MCBS 4; ESCAT I-A]\n"
    "Crizotinib [I, B; MCBS 4; ESCAT I-A]\n"
    "Ceritinib [I, B; MCBS 4; ESCAT I-A]"
)
REBIOPSY_ALK = "Rebiopsy recommended (not mandatory for decision)"
AFTER_CRIZOTINIB_TX = (
    "Alectinib [I, A; MCBS 4; ESCAT I-A]\n"
    "Brigatinib [III, A; MCBS 4; ESCAT I-A]\n"
    "Ceritinib [I, A; MCBS 4; ESCAT I-A]"
)
LATE_LINE = (
    "Lorlatinib [III, A; MCBS 4; ESCAT I-A]\n"
    "Platinum-pemetrexed ChT [III, A]\n"
    "Atezolizumab-bevacizumab-paclitaxel-carboplatin [III, B; MCBS 3]"
)

alk_graph = load_dg(ALK_DG)

ALK_EXAMPLES = [
    Data(set()),
    Data(("Oligoprogression",)),
    Data(("Systemic_progression",)),
    Data(("Systemic_progression", "after_crizotinib")),
    Data(("Systemic_progression", "after_crizotinib", "no_lorlatinib")),

]


class MnsclcAlkSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(alk_graph),
            {
                "Oligoprogression": "tag",
                "Systemic_progression": "tag",
                "after_crizotinib": "tag",
                "after_ALK_TKI_not_crizotinib": "tag",
                "no_lorlatinib": "tag",
            },
        )


class MnsclcAlkWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_disease_progression(self):
        x = Data(set())
        self.assertEqual(validate_data(infer_schema(alk_graph), x), [])
        self.assertEqual(
            walk(alk_graph, x),
            (
                [[ALK_ROOT_LABEL, FIRST_LINE_ALK, "Disease progression"]],
                ["Oligoprogression", "Systemic_progression"],
            ),
        )

    def test_example_2_oligoprogression_stops_at_rebiopsy(self):
        x = Data(("Oligoprogression",))
        self.assertEqual(validate_data(infer_schema(alk_graph), x), [])
        self.assertEqual(
            walk(alk_graph, x),
            (
                [[
                    ALK_ROOT_LABEL,
                    FIRST_LINE_ALK,
                    "Disease progression",
                    "Oligoprogression",
                    LOCAL_TREATMENT,
                    "Systemic progression",
                    REBIOPSY_ALK,
                ]],
                ["after_crizotinib", "after_ALK_TKI_not_crizotinib"],
            ),
        )

    def test_example_3_systemic_progression_stops_at_rebiopsy(self):
        x = Data(("Systemic_progression",))
        self.assertEqual(validate_data(infer_schema(alk_graph), x), [])
        self.assertEqual(
            walk(alk_graph, x),
            (
                [[
                    ALK_ROOT_LABEL,
                    FIRST_LINE_ALK,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY_ALK,
                ]],
                ["after_crizotinib", "after_ALK_TKI_not_crizotinib"],
            ),
        )

    def test_example_4_after_crizotinib_stops_at_late_systemic_progression(self):
        x = Data(("Systemic_progression", "after_crizotinib"))
        self.assertEqual(validate_data(infer_schema(alk_graph), x), [])
        self.assertEqual(
            walk(alk_graph, x),
            (
                [[
                    ALK_ROOT_LABEL,
                    FIRST_LINE_ALK,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY_ALK,
                    "after_crizotinib",
                    AFTER_CRIZOTINIB_TX,
                    "Systemic progression",
                ]],
                ["no_lorlatinib"],
            ),
        )

    def test_example_5_after_crizotinib_no_lorlatinib_reaches_late_line(self):
        x = Data(("Systemic_progression", "after_crizotinib", "no_lorlatinib"))
        self.assertEqual(validate_data(infer_schema(alk_graph), x), [])
        self.assertEqual(
            walk(alk_graph, x),
            (
                [[
                    ALK_ROOT_LABEL,
                    FIRST_LINE_ALK,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY_ALK,
                    "after_crizotinib",
                    AFTER_CRIZOTINIB_TX,
                    "Systemic progression",
                    "no_lorlatinib",
                    LATE_LINE,
                ]],
                [],
            ),
        )


class MnsclcAlkEquivalenceTests(unittest.TestCase):
    def test_dot_to_graph_agrees_before_late_line_gate(self):
        graph1 = dot_to_graph(ALK_DOT.read_text())
        graph2 = load_dg(ALK_DG)
        early_examples = ALK_EXAMPLES[:3]
        for x in early_examples:
            paths1, required1 = walk(graph1, x)
            paths2, required2 = walk(graph2, x)
            self.assertEqual(
                [[node.label for node in path.path] for path in paths1],
                [[node.label for node in path.path] for path in paths2],
            )
            self.assertEqual(required1, required2)

    def test_curated_dg_gates_late_line_on_no_lorlatinib(self):
        x = Data(("Systemic_progression", "after_crizotinib"))
        dot_paths, dot_required = walk(dot_to_graph(ALK_DOT.read_text()), x)
        dg_paths, dg_required = walk(load_dg(ALK_DG), x)
        self.assertEqual(dg_required, ["no_lorlatinib"])
        self.assertEqual(dot_required, [])
        self.assertIn(LATE_LINE, [node.label for node in dot_paths[0].path])
        self.assertNotIn(LATE_LINE, [node.label for node in dg_paths[0].path])


if __name__ == "__main__":
    unittest.main()
