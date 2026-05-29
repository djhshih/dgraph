import unittest

from dgraph.condition import Condition
from dgraph.graph import Data
from dgraph.logic import And, Group, Or, Phrase, PrefixCompare, infer_condition, parse


class LogicParserTests(unittest.TestCase):
    def test_parse_atomic_phrase(self):
        expr = parse("Primary surgery indicated")
        self.assertEqual(expr, Phrase("Primary surgery indicated"))

    def test_parse_or(self):
        expr = parse("SLN- or TAD-")
        self.assertEqual(expr, Or(Phrase("SLN-"), Phrase("TAD-")))

    def test_parse_and_precedence(self):
        expr = parse("gBRCA1/2m and stage III or high-risk non-pCR")
        self.assertEqual(
            expr,
            Or(
                And(Phrase("gBRCA1/2m"), Phrase("stage III")),
                Phrase("high-risk non-pCR"),
            ),
        )

    def test_parse_parentheses(self):
        expr = parse("gBRCA1/2m and (stage III or high-risk non-pCR)")
        self.assertEqual(
            expr,
            And(
                Phrase("gBRCA1/2m"),
                Group(Or(Phrase("stage III"), Phrase("high-risk non-pCR"))),
            ),
        )

    def test_newlines_are_phrase_separators_not_or(self):
        expr = parse("Luminal A-like stage II-III\nLuminal B-like stage I-III")
        self.assertEqual(expr, Phrase("Luminal A-like stage II-III Luminal B-like stage I-III"))

    def test_parse_prefix_comparison_with_explicit_value(self):
        expr = parse("> 2 positive_nodes")
        self.assertEqual(expr, PrefixCompare(">", Phrase("2"), Phrase("positive_nodes")))

    def test_parse_prefix_comparison_with_embedded_value(self):
        expr = parse(">= cT2")
        self.assertEqual(expr, PrefixCompare(">=", None, Phrase("cT2")))

    def test_parse_comparison_binds_tighter_than_and_or(self):
        expr = parse("> 2 positive_nodes and N0 or HER2+")
        self.assertEqual(
            expr,
            Or(
                And(
                    PrefixCompare(">", Phrase("2"), Phrase("positive_nodes")),
                    Phrase("N0"),
                ),
                Phrase("HER2+"),
            ),
        )


class LogicInterpretTests(unittest.TestCase):
    def test_compile_atomic_phrase_to_has(self):
        cond = infer_condition("Primary surgery indicated")
        self.assertIsInstance(cond, Condition)
        self.assertTrue(cond(Data(tags={"Primary surgery indicated"})))
        self.assertFalse(cond(Data(tags={"other"})))

    def test_compile_or(self):
        cond = infer_condition("SLN- or TAD-")
        self.assertTrue(cond(Data(tags={"SLN-"})))
        self.assertTrue(cond(Data(tags={"TAD-"})))
        self.assertFalse(cond(Data(tags={"SLN+"})))

    def test_compile_phrase_is_atomic_by_default(self):
        cond = infer_condition("HR+/HER2-")
        self.assertTrue(cond(Data(tags={"HR+/HER2-"})))
        self.assertFalse(cond(Data(tags={"HR+", "HER2-"})))

    def test_compile_prefix_comparison_with_explicit_value(self):
        class X:
            def __init__(self, positive_nodes):
                self.positive_nodes = positive_nodes

        cond = infer_condition("> 2 positive_nodes")
        self.assertTrue(cond(X(3)))
        self.assertFalse(cond(X(2)))
        self.assertEqual(cond.attrs, ("positive_nodes",))

    def test_compile_prefix_comparison_with_embedded_value(self):
        class X:
            def __init__(self, cT2):
                self.cT2 = cT2

        cond = infer_condition(">= cT2")
        self.assertTrue(cond(X(2)))
        self.assertFalse(cond(X(1)))
        self.assertEqual(cond.attrs, ("cT2",))


if __name__ == "__main__":
    unittest.main()
