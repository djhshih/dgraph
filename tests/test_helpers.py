import unittest

import dgraph.condition as dc
from dgraph.graph import Data, Node, branch, case, chain, match, node, walk
from dgraph.schema import infer_schema, validate_data


class HelperTests(unittest.TestCase):
    def test_node(self):
        graph = node("root", branch("yes", dc.has("neoadjuvant"), Node("leaf")))
        self.assertEqual(walk(graph, Data(("neoadjuvant",))), ([["root", "yes", "leaf"]], []))
        self.assertEqual(walk(graph, Data(set())), ([["root"]], [("neoadjuvant",)]))

    def test_chain(self):
        graph = node("root", chain("A", "B", "C"))
        self.assertEqual(walk(graph, Data(set())), ([["root", "A", "B", "C"]], []))

    def test_match(self):
        graph = node(
            "root",
            match(
                "tags",
                case("x", Node("X")),
                case(("y", "z"), Node("YZ")),
            ),
        )

        class X:
            def __init__(self, tags):
                self.tags = tags

        self.assertEqual(walk(graph, X("x")), ([["root", "x", "X"]], []))
        self.assertEqual(walk(graph, X("y")), ([["root", "y/z", "YZ"]], []))
        self.assertEqual(walk(graph, X("z")), ([["root", "y/z", "YZ"]], []))

    def test_infer_schema(self):
        graph = node(
            "root",
            branch("yes", dc.has("neoadjuvant"), Node("leaf")),
            branch("many", dc.gt("positive_nodes", 2), Node("leaf")),
            match(
                "kind",
                case("x", Node("X")),
                case(("y", "z"), Node("YZ")),
            ),
        )
        schema = infer_schema(graph)
        self.assertEqual(schema["neoadjuvant"], "tag")
        self.assertEqual(schema["positive_nodes"], "unknown")
        self.assertEqual(schema["kind"], "unknown")

    def test_validate_data_success_tuple_membership(self):
        graph = node(
            "root",
            branch("yes", dc.has("neoadjuvant"), Node("leaf")),
            branch("many", dc.gt("positive_nodes", 2), Node("leaf")),
            match("kind", case("x", Node("X")), case(("y", "z"), Node("YZ"))),
        )
        schema = infer_schema(graph)

        class X:
            def __init__(self):
                self.tags = ("neoadjuvant",)
                self.kind = "x"
                self.positive_nodes = 3

        errors = validate_data(schema, X())
        self.assertEqual(errors, [])

    def test_validate_data_success_set(self):
        graph = node(
            "root",
            branch("yes", dc.has("neoadjuvant"), Node("leaf")),
            branch("many", dc.gt("positive_nodes", 2), Node("leaf")),
            match("kind", case("x", Node("X")), case(("y", "z"), Node("YZ"))),
        )
        schema = infer_schema(graph)

        class X:
            def __init__(self):
                self.tags = {"neoadjuvant"}
                self.kind = "x"
                self.positive_nodes = 3

        errors = validate_data(schema, X())
        self.assertEqual(errors, [])

    def test_validate_data_missing_field(self):
        class PartialData:
            pass

        graph = node("root", branch("yes", dc.has("neoadjuvant"), Node("leaf")))
        schema = infer_schema(graph)
        errors = validate_data(schema, PartialData())
        self.assertEqual(errors, [])

    def test_validate_data_bad_value(self):
        graph = node("root", match("kind", case("x", Node("X")), case(("y", "z"), Node("YZ"))))
        schema = infer_schema(graph)

        class X:
            def __init__(self):
                self.kind = "q"

        errors = validate_data(schema, X())
        self.assertEqual(errors, [])

    def test_validate_data_bad_tag_type(self):
        graph = node("root", branch("yes", dc.has("neoadjuvant"), Node("leaf")))
        schema = infer_schema(graph)

        class X:
            def __init__(self):
                self.tags = "neoadjuvant"

        errors = validate_data(schema, X())
        self.assertEqual(errors, ["Field 'tags' expected kind tag, got value 'neoadjuvant'"])


if __name__ == "__main__":
    unittest.main()
