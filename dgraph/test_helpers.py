import unittest
from dataclasses import dataclass

import dgraph.condition as dc
from dgraph.graph import Node, branch, case, chain, infer_schema, match, node, walk


@dataclass
class Data:
    kind: str | None = None
    neoadjuvant: bool | None = None
    positive_nodes: int | None = None


class HelperTests(unittest.TestCase):
    def test_node(self):
        graph = node("root", branch("yes", dc.is_true("neoadjuvant"), Node("leaf")))
        self.assertEqual(walk(graph, Data(neoadjuvant=True)), [["root", "yes", "leaf"]])
        self.assertEqual(walk(graph, Data(neoadjuvant=False)), [["root"]])

    def test_chain(self):
        graph = node("root", chain("A", "B", "C"))
        self.assertEqual(walk(graph, Data()), [["root", "A", "B", "C"]])

    def test_match(self):
        graph = node(
            "root",
            *match(
                "kind",
                case("x", Node("X")),
                case(("y", "z"), Node("YZ")),
            ),
        )
        self.assertEqual(walk(graph, Data(kind="x")), [["root", "x", "X"]])
        self.assertEqual(walk(graph, Data(kind="y")), [["root", "y/z", "YZ"]])
        self.assertEqual(walk(graph, Data(kind="z")), [["root", "y/z", "YZ"]])

    def test_infer_schema(self):
        graph = node(
            "root",
            branch("yes", dc.is_true("neoadjuvant"), Node("leaf")),
            branch("many", dc.gt("positive_nodes", 2), Node("leaf")),
            *match(
                "kind",
                case("x", Node("X")),
                case(("y", "z"), Node("YZ")),
            ),
        )
        schema = infer_schema(graph)
        self.assertEqual(schema["neoadjuvant"]["kind"], "bool")
        self.assertEqual(schema["positive_nodes"]["kind"], "number")
        self.assertEqual(schema["kind"]["kind"], "categorical")
        self.assertEqual(schema["kind"]["observed_values"], ["x", "y", "z"])
        self.assertEqual(schema["positive_nodes"]["numeric_thresholds"], [("gt", 2)])


if __name__ == "__main__":
    unittest.main()
