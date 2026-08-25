import unittest

from dgraph.condition import Condition
from dgraph.graph import Data
from dgraph.logic import And, Group, Or, Phrase, PrefixCompare, compile_expr_from_text, condition_helpers_from_text, infer_condition, parse


class LogicParserTests(unittest.TestCase):
    def test_parse_atomic_phrase(self):
        expr = parse("HER2+")
        self.assertEqual(expr, Phrase("HER2+"))

    def test_parse_or(self):
        expr = parse("SLN- or TAD-")
        self.assertEqual(expr, Or(Phrase("SLN-"), Phrase("TAD-")))

    def test_parse_and_precedence(self):
        expr = parse("gBRCA1/2m and stage_III or high-risk_non-pCR")
        self.assertEqual(
            expr,
            Or(
                And(Phrase("gBRCA1/2m"), Phrase("stage_III")),
                Phrase("high-risk_non-pCR"),
            ),
        )

    def test_parse_parentheses(self):
        expr = parse("gBRCA1/2m and (stage_III or high-risk_non-pCR)")
        self.assertEqual(
            expr,
            And(
                Phrase("gBRCA1/2m"),
                Group(Or(Phrase("stage_III"), Phrase("high-risk_non-pCR"))),
            ),
        )

    def test_parse_newlines_as_implicit_or(self):
        expr = parse("cT1b N0\nHER2+")
        self.assertEqual(
            expr,
            Or(
                And(Phrase("cT1b"), Phrase("N0")),
                Phrase("HER2+"),
            ),
        )

    def test_parse_or_on_its_own_line(self):
        expr = parse("Everolimus-exemestane\nor\nEverolimus-fulvestrant")
        self.assertEqual(
            expr,
            Or(Phrase("Everolimus-exemestane"), Phrase("Everolimus-fulvestrant")),
        )

    def test_parse_repeated_or_on_its_own_line(self):
        expr = parse("A\nor\nB\nor\nC")
        self.assertEqual(expr, Or(Or(Phrase("A"), Phrase("B")), Phrase("C")))

    def test_parse_and_on_its_own_line(self):
        expr = parse("EGFR_WT\nand\nALK_WT")
        self.assertEqual(expr, And(Phrase("EGFR_WT"), Phrase("ALK_WT")))

    def test_parse_or_on_its_own_line_with_evidence_tags(self):
        expr = parse("Everolimus-exemestane [I, B]\nor\nEverolimus-fulvestrant [II, B]")
        self.assertEqual(
            expr,
            Or(Phrase("Everolimus-exemestane"), Phrase("Everolimus-fulvestrant")),
        )

    def test_parse_spaces_as_implicit_and(self):
        expr = parse("cT1b N0 HER2+")
        self.assertEqual(
            expr,
            And(And(Phrase("cT1b"), Phrase("N0")), Phrase("HER2+")),
        )

    def test_parse_prefix_comparison_with_explicit_value(self):
        expr = parse("> 2 positive_nodes")
        self.assertIsInstance(expr, And)

    def test_parse_prefix_comparison_with_embedded_value(self):
        expr = parse(">= cT2")
        self.assertEqual(expr, PrefixCompare(">=", None, Phrase("cT2")))

    def test_parse_comparison_binds_tighter_than_and_or(self):
        expr = parse("> 2 positive_nodes and N0\nHER2+")
        self.assertIsInstance(expr, Or)

    def test_parse_strips_simple_evidence_tag(self):
        expr = parse("Carboplatin-pemetrexed [I, A]")
        self.assertEqual(expr, Phrase("Carboplatin-pemetrexed"))

    def test_parse_strips_mcbs_evidence_tag(self):
        expr = parse("Cisplatin-pemetrexed [I, A; MCBS 3]")
        self.assertEqual(expr, Phrase("Cisplatin-pemetrexed"))

    def test_parse_strips_escat_evidence_tag(self):
        expr = parse("Alectinib [I, A; MCBS 4; ESCAT I-A]")
        self.assertEqual(expr, Phrase("Alectinib"))

    def test_parse_strips_bare_escat_tag(self):
        expr = parse("dMMR or MSI-H [ESCAT I-A]")
        self.assertEqual(expr, Or(Phrase("dMMR"), Phrase("MSI-H")))

    def test_parse_strips_escat_na_tag(self):
        expr = parse("RAS_mutated [ESCAT NA]")
        self.assertEqual(expr, Phrase("RAS_mutated"))

    def test_parse_strips_mcbs_with_parenthetical(self):
        expr = parse("Osimertinib for 3 years [I, A; MCBS A (AT)]")
        self.assertEqual(
            expr,
            And(And(And(Phrase("Osimertinib"), Phrase("for")), Phrase("3")), Phrase("years")),
        )


class LogicInterpretTests(unittest.TestCase):
    def test_compile_atomic_phrase_to_has(self):
        cond = infer_condition("HER2+")
        self.assertIsInstance(cond, Condition)
        self.assertTrue(cond(Data(tags={"HER2+"})))
        self.assertFalse(cond(Data(tags={"other"})))

    def test_compile_or(self):
        cond = infer_condition("SLN- or TAD-")
        self.assertTrue(cond(Data(tags={"SLN-"})))
        self.assertTrue(cond(Data(tags={"TAD-"})))
        self.assertFalse(cond(Data(tags={"SLN+"})))

    def test_compile_implicit_and(self):
        cond = infer_condition("cT1b N0")
        self.assertTrue(cond(Data(tags={"cT1b", "N0"})))
        self.assertFalse(cond(Data(tags={"cT1b"})))

    def test_compile_implicit_or_between_lines(self):
        cond = infer_condition("SLN-\nTAD-")
        self.assertTrue(cond(Data(tags={"SLN-"})))
        self.assertTrue(cond(Data(tags={"TAD-"})))
        self.assertFalse(cond(Data(tags={"SLN+"})))

    def test_compile_phrase_is_atomic_by_default(self):
        cond = infer_condition("HR+/HER2-")
        self.assertTrue(cond(Data(tags={"HR+/HER2-"})))
        self.assertFalse(cond(Data(tags={"HR+", "HER2-"})))

    def test_compile_and_codegen_use_implicit_ops(self):
        self.assertEqual(
            compile_expr_from_text("SLN-\nTAD+"),
            "any_of(has('SLN-'), has('TAD+'))"
        )
        self.assertEqual(
            condition_helpers_from_text("cT1b N0\nHER2+"),
            ("all_of", "any_of", "has"),
        )

    def test_compile_prefix_comparison_with_explicit_value(self):
        cond = infer_condition(">= cT2")
        self.assertTrue(cond(Data(tags={">=cT2"})))
        self.assertFalse(cond(Data(tags={"cT2"})))

    def test_compile_prefix_comparison_with_embedded_value_is_atomic_for_now(self):
        cond = infer_condition(">= cT2")
        self.assertTrue(cond(Data(tags={">=cT2"})))


if __name__ == "__main__":
    unittest.main()
