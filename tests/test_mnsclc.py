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


EGFR_DG = ROOT / "data/mnsclc/dg/mnsclc_egfr.dg"
EGFR_DOT = ROOT / "data/mnsclc/dot/mnsclc_egfr.dot"

EGFR_ROOT_LABEL = "Stage IV mNSCLC with EGFR-activating mutation"
PS_GATE = "PS 0-2 [I, A]\nPS 3-4 for all following options [III, A]"
FIRST_LINE_EGFR = (
    "Osimertinib [I, A; MCBS 4; ESCAT I-A]\n"
    "Gefitinib [I, B; MCBS 4; ESCAT I-A]\n"
    "Erlotinib [I, B; MCBS 4; ESCAT I-A]\n"
    "Erlotinib-bevacizumab [I, B; MCBS 2; ESCAT I-A]\n"
    "Erlotinib-ramucirumab [I, B; MCBS 3; ESCAT I-A]\n"
    "Afatinib [I, B; MCBS 5; ESCAT I-A]\n"
    "Dacomitinib [I, B; MCBS 3; ESCAT I-A]\n"
    "Gefitinib-carboplatin-pemetrexed [I, B]"
)
REBIOPSY_EGFR = (
    "Rebiopsy or cfDNA plasma testing (at least T790M for progression on first/second-generation TKI [I, A], "
    "NGS for progression on osimertinib [III, C], with rebiopsy if plasma test is negative)"
)
EGFR_PLATINUM = (
    "Platinum-based ChT [III, A]\n"
    "Atezolizumab-bevacizumab-paclitaxel-carboplatin [III, B; MCBS 3]"
)
OSIMERTINIB_SECOND_LINE = "Osimertinib [I, A; MCBS 4; ESCAT I-A]"

T790M_NEGATIVE_OR_REBIOPSY = "Exon_20_T790M_mutation_negative or rebiopsy_indicated_but_not_feasible"

egfr_graph = load_dg(EGFR_DG)

EGFR_EXAMPLES = [
    Data(set()),
    Data(("Oligoprogression",)),
    Data(("Systemic_progression",)),
    Data(("Systemic_progression", "first_line_osimertinib", "No_resistance_mechanism_identified")),
    Data(("Systemic_progression", "first_line_first_or_second_generation_TKI", "Exon_20_T790M_mutation_positive")),
    Data(("Systemic_progression", "first_line_first_or_second_generation_TKI", "Exon_20_T790M_mutation_negative")),
]


class MnsclcEgfrSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(
            infer_schema(egfr_graph),
            {
                "Oligoprogression": "tag",
                "Systemic_progression": "tag",
                "first_line_osimertinib": "tag",
                "first_line_first_or_second_generation_TKI": "tag",
                "Resistance_mechanism_identified": "tag",
                "No_resistance_mechanism_identified": "tag",
                "Exon_20_T790M_mutation_positive": "tag",
                "Exon_20_T790M_mutation_negative": "tag",
                "rebiopsy_indicated_but_not_feasible": "tag",
            },
        )


class MnsclcEgfrWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_disease_progression(self):
        x = Data(set())
        self.assertEqual(validate_data(infer_schema(egfr_graph), x), [])
        self.assertEqual(
            walk(egfr_graph, x),
            (
                [[EGFR_ROOT_LABEL, PS_GATE, FIRST_LINE_EGFR, "Disease progression"]],
                ["Oligoprogression", "Systemic_progression"],
            ),
        )

    def test_example_2_oligoprogression_stops_at_rebiopsy(self):
        x = Data(("Oligoprogression",))
        self.assertEqual(validate_data(infer_schema(egfr_graph), x), [])
        self.assertEqual(
            walk(egfr_graph, x),
            (
                [[
                    EGFR_ROOT_LABEL,
                    PS_GATE,
                    FIRST_LINE_EGFR,
                    "Disease progression",
                    "Oligoprogression",
                    LOCAL_TREATMENT,
                    "Systemic progression",
                    REBIOPSY_EGFR,
                ]],
                ["first_line_osimertinib", "first_line_first_or_second_generation_TKI"],
            ),
        )

    def test_example_3_systemic_progression_stops_at_rebiopsy(self):
        x = Data(("Systemic_progression",))
        self.assertEqual(validate_data(infer_schema(egfr_graph), x), [])
        self.assertEqual(
            walk(egfr_graph, x),
            (
                [[
                    EGFR_ROOT_LABEL,
                    PS_GATE,
                    FIRST_LINE_EGFR,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY_EGFR,
                ]],
                ["first_line_osimertinib", "first_line_first_or_second_generation_TKI"],
            ),
        )

    def test_example_4_osimertinib_no_resistance_reaches_platinum(self):
        x = Data(("Systemic_progression", "first_line_osimertinib", "No_resistance_mechanism_identified"))
        self.assertEqual(validate_data(infer_schema(egfr_graph), x), [])
        self.assertEqual(
            walk(egfr_graph, x),
            (
                [[
                    EGFR_ROOT_LABEL,
                    PS_GATE,
                    FIRST_LINE_EGFR,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY_EGFR,
                    "first_line_osimertinib",
                    "No_resistance_mechanism_identified",
                    EGFR_PLATINUM,
                ]],
                [],
            ),
        )

    def test_example_5_first_gen_tki_t790m_positive_reaches_platinum(self):
        x = Data(("Systemic_progression", "first_line_first_or_second_generation_TKI", "Exon_20_T790M_mutation_positive"))
        self.assertEqual(validate_data(infer_schema(egfr_graph), x), [])
        self.assertEqual(
            walk(egfr_graph, x),
            (
                [[
                    EGFR_ROOT_LABEL,
                    PS_GATE,
                    FIRST_LINE_EGFR,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY_EGFR,
                    "first_line_first_or_second_generation_TKI",
                    "Exon_20_T790M_mutation_positive",
                    OSIMERTINIB_SECOND_LINE,
                    "Systemic progression",
                    EGFR_PLATINUM,
                ]],
                [],
            ),
        )

    def test_example_6_first_gen_tki_t790m_negative_reaches_platinum(self):
        x = Data(("Systemic_progression", "first_line_first_or_second_generation_TKI", "Exon_20_T790M_mutation_negative"))
        self.assertEqual(validate_data(infer_schema(egfr_graph), x), [])
        self.assertEqual(
            walk(egfr_graph, x),
            (
                [[
                    EGFR_ROOT_LABEL,
                    PS_GATE,
                    FIRST_LINE_EGFR,
                    "Disease progression",
                    "Systemic_progression",
                    REBIOPSY_EGFR,
                    "first_line_first_or_second_generation_TKI",
                    T790M_NEGATIVE_OR_REBIOPSY,
                    EGFR_PLATINUM,
                ]],
                [],
            ),
        )


class MnsclcEgfrEquivalenceTests(unittest.TestCase):
    def test_dot_to_graph_matches_curated_dg(self):
        graph1 = dot_to_graph(EGFR_DOT.read_text())
        graph2 = load_dg(EGFR_DG)
        self.assertEqual(infer_schema(graph1), infer_schema(graph2))
        for x in EGFR_EXAMPLES:
            self.assertEqual(walk(graph1, x), walk(graph2, x))

    def test_walk_paths_have_no_compiler_placeholders(self):
        for x in EGFR_EXAMPLES:
            paths, _ = walk(egfr_graph, x)
            for path in paths:
                for node in path.path:
                    self.assertNotIn(node.label, {"n", "o", "p", "root", "node"})


### --------------------------------------------- mol-pos ---------------------------------------------
MOL_POS_DG = ROOT / "data/mnsclc/dg/mnsclc_mol_pos.dg"
MOL_POS_DOT = ROOT / "data/mnsclc/dot/mnsclc_mol_pos.dot"

MOL_POS_ROOT = "Stage IV mNSCLC molecular tests positive"
BIOMARKER_REQUIRED = [
    "EGFR_mutation",
    "ALK_translocation",
    "ROS1_translocation",
    "BRAF_V600_mutation",
    "RET_translocation",
    "NTRK_translocation",
    "HER2_mutation",
    "EGFR_ex20ins_mutation",
    "MET_ex14_skipping_mutation",
    "KRAS_G12C_mutation",
]
RET_TX = "Pralsetinib [III, A; MCBS 3; ESCAT I-C]\nSelpercatinib [III, A; MCBS 3; ESCAT I-C]"

mol_pos_graph = load_dg(MOL_POS_DG)

MOL_POS_EXAMPLES = [
    Data(set()),
    Data(("EGFR_mutation",)),
    Data(("ALK_translocation",)),
    Data(("ROS1_translocation",)),
    Data(("BRAF_V600_mutation",)),
    Data(("RET_translocation",)),
]

MOL_POS_SCHEMA = {
    "EGFR_mutation": "tag",
    "Oligoprogression": "tag",
    "first_line_osimertinib": "tag",
    "Resistance_mechanism_identified": "tag",
    "No_resistance_mechanism_identified": "tag",
    "first_line_first_or_second_generation_TKI": "tag",
    "Exon_20_T790M_mutation_positive": "tag",
    "Exon_20_T790M_mutation_negative": "tag",
    "rebiopsy_indicated_but_not_feasible": "tag",
    "Systemic_progression": "tag",
    "ALK_translocation": "tag",
    "after_crizotinib": "tag",
    "no_lorlatinib": "tag",
    "after_ALK_TKI_not_crizotinib": "tag",
    "ROS1_translocation": "tag",
    "no_ROS1_TKI_received_in_first_line": "tag",
    "ROS1_TKI_received_in_first_line": "tag",
    "BRAF_V600_mutation": "tag",
    "no_smoking_history": "tag",
    "smoking_history": "tag",
    "RET_translocation": "tag",
    "NTRK_translocation": "tag",
    "HER2_mutation": "tag",
    "EGFR_ex20ins_mutation": "tag",
    "MET_ex14_skipping_mutation": "tag",
    "KRAS_G12C_mutation": "tag",
    "if_ICI_monotherapy_given_in_first_line": "tag",
    "if_ICI_monotherapy_not_given_in_first_line": "tag",
}


class MnsclcMolPosSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        self.assertEqual(infer_schema(mol_pos_graph), MOL_POS_SCHEMA)


class MnsclcMolPosWalkTests(unittest.TestCase):
    def test_example_1_no_tags_stops_at_biomarker_frontier(self):
        x = Data(set())
        self.assertEqual(validate_data(infer_schema(mol_pos_graph), x), [])
        self.assertEqual(
            walk(mol_pos_graph, x),
            ([[MOL_POS_ROOT]], BIOMARKER_REQUIRED),
        )

    def test_example_2_egfr_delegates_to_disease_progression(self):
        x = Data(("EGFR_mutation",))
        self.assertEqual(validate_data(infer_schema(mol_pos_graph), x), [])
        self.assertEqual(
            walk(mol_pos_graph, x),
            (
                [[
                    MOL_POS_ROOT,
                    "EGFR_mutation",
                    EGFR_ROOT_LABEL,
                    PS_GATE,
                    FIRST_LINE_EGFR,
                    "Disease progression",
                ]],
                ["Oligoprogression", "Systemic_progression"],
            ),
        )

    def test_example_3_alk_delegates_to_disease_progression(self):
        x = Data(("ALK_translocation",))
        self.assertEqual(validate_data(infer_schema(mol_pos_graph), x), [])
        self.assertEqual(
            walk(mol_pos_graph, x),
            (
                [[
                    MOL_POS_ROOT,
                    "ALK_translocation",
                    ALK_ROOT_LABEL,
                    FIRST_LINE_ALK,
                    "Disease progression",
                ]],
                ["Oligoprogression", "Systemic_progression"],
            ),
        )

    def test_example_4_ros1_delegates_to_disease_progression(self):
        x = Data(("ROS1_translocation",))
        self.assertEqual(validate_data(infer_schema(mol_pos_graph), x), [])
        self.assertEqual(
            walk(mol_pos_graph, x),
            (
                [[
                    MOL_POS_ROOT,
                    "ROS1_translocation",
                    ROOT_LABEL,
                    FIRST_LINE_TKIS,
                    "Disease progression",
                ]],
                ["Oligoprogression", "Systemic_progression"],
            ),
        )

    def test_example_5_braf_delegates_to_disease_progression(self):
        x = Data(("BRAF_V600_mutation",))
        self.assertEqual(validate_data(infer_schema(mol_pos_graph), x), [])
        self.assertEqual(
            walk(mol_pos_graph, x),
            (
                [[
                    MOL_POS_ROOT,
                    "BRAF_V600_mutation",
                    BRAF_ROOT_LABEL,
                    FIRST_LINE,
                    "Disease_progression",
                ]],
                ["Oligoprogression", "Systemic_progression"],
            ),
        )

    def test_example_6_ret_inline_path_reaches_leaf(self):
        x = Data(("RET_translocation",))
        self.assertEqual(validate_data(infer_schema(mol_pos_graph), x), [])
        self.assertEqual(
            walk(mol_pos_graph, x),
            (
                [[MOL_POS_ROOT, "RET_translocation", RET_TX]],
                [],
            ),
        )


class MnsclcMolPosCompositionTests(unittest.TestCase):
    def test_egfr_path_suffix_matches_standalone_graph(self):
        x = Data(("EGFR_mutation",))
        mol_paths, mol_req = walk(mol_pos_graph, x)
        egfr_paths, egfr_req = walk(egfr_graph, Data(set()))
        self.assertEqual(
            [n.label for n in mol_paths[0].path][2:],
            [n.label for n in egfr_paths[0].path],
        )
        self.assertEqual(mol_req, egfr_req)

    def test_alk_path_suffix_matches_standalone_graph(self):
        x = Data(("ALK_translocation",))
        mol_paths, mol_req = walk(mol_pos_graph, x)
        alk_paths, alk_req = walk(alk_graph, Data(set()))
        self.assertEqual(
            [n.label for n in mol_paths[0].path][2:],
            [n.label for n in alk_paths[0].path],
        )
        self.assertEqual(mol_req, alk_req)

    def test_ros1_path_suffix_matches_standalone_graph(self):
        x = Data(("ROS1_translocation",))
        mol_paths, mol_req = walk(mol_pos_graph, x)
        ros1_paths, ros1_req = walk(graph, Data(set()))
        self.assertEqual(
            [n.label for n in mol_paths[0].path][2:],
            [n.label for n in ros1_paths[0].path],
        )
        self.assertEqual(mol_req, ros1_req)

    def test_braf_path_suffix_matches_standalone_graph(self):
        x = Data(("BRAF_V600_mutation",))
        mol_paths, mol_req = walk(mol_pos_graph, x)
        braf_paths, braf_req = walk(braf_graph, Data(set()))
        self.assertEqual(
            [n.label for n in mol_paths[0].path][2:],
            [n.label for n in braf_paths[0].path],
        )
        self.assertEqual(mol_req, braf_req)


class MnsclcMolPosEquivalenceTests(unittest.TestCase):
    def _walk_labels(self, graph, x):
        paths, required = walk(graph, x)
        return (
            [[node.label for node in path.path] for path in paths],
            required,
        )

    def test_dot_to_graph_matches_curated_dg_at_router_frontier(self):
        dot_graph = dot_to_graph(MOL_POS_DOT.read_text())
        x = Data(set())
        self.assertEqual(
            self._walk_labels(dot_graph, x),
            self._walk_labels(mol_pos_graph, x),
        )

    def test_dot_to_graph_matches_curated_dg_for_inline_ret_path(self):
        dot_graph = dot_to_graph(MOL_POS_DOT.read_text())
        x = Data(("RET_translocation",))
        self.assertEqual(
            self._walk_labels(dot_graph, x),
            self._walk_labels(mol_pos_graph, x),
        )

    def test_curated_dg_delegates_egfr_past_first_line_leaf(self):
        dot_graph = dot_to_graph(MOL_POS_DOT.read_text())
        x = Data(("EGFR_mutation",))
        dot_paths, dot_required = walk(dot_graph, x)
        dg_paths, dg_required = walk(mol_pos_graph, x)
        self.assertEqual(dot_required, [])
        self.assertEqual(dg_required, ["Oligoprogression", "Systemic_progression"])
        self.assertEqual(dot_paths[0].path[-1].label, FIRST_LINE_EGFR)
        self.assertEqual(dg_paths[0].path[-1].label, "Disease progression")


if __name__ == "__main__":
    unittest.main()
