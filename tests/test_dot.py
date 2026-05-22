import unittest

from dgraph.dot import analyze_dot_graph, build_graph, dot_to_forest, dot_to_graph, find_roots, infer_condition_from_label, parse_dot, parse_dot_with_metadata
from dgraph.graph import Data, infer_schema, walk


class ParseDotTests(unittest.TestCase):
    def test_parse_nodes_and_edges(self):
        dot = '''
        digraph G {
          rankdir=TB;
          a [label="Root", shape=box];
          b [label="Left", shape=box];
          c [label="Right", shape=box];
          a -> b;
          a -> c;
        }
        '''
        labels, edges = parse_dot(dot)
        self.assertEqual(labels["a"], "Root")
        self.assertEqual(labels["b"], "Left")
        self.assertEqual(labels["c"], "Right")
        self.assertEqual(edges, [("a", "b"), ("a", "c")])

    def test_parse_missing_label_falls_back_to_id(self):
        dot = '''
        digraph G {
          a [shape=box];
        }
        '''
        labels, edges = parse_dot(dot)
        self.assertEqual(labels, {"a": "a"})
        self.assertEqual(edges, [])

    def test_parse_duplicate_labels_preserved_by_id(self):
        dot = '''
        digraph G {
          a [label="X"];
          b [label="X"];
        }
        '''
        labels, _ = parse_dot(dot)
        self.assertEqual(labels, {"a": "X", "b": "X"})

    def test_parse_chained_edges(self):
        dot = '''
        digraph G {
          a -> b -> c;
        }
        '''
        _, edges = parse_dot(dot)
        self.assertEqual(edges, [("a", "b"), ("b", "c")])

    def test_parse_label_unescapes_common_sequences(self):
        dot = r'''
        digraph G {
          a [label="Line\nTwo \"Q\""];
        }
        '''
        labels, _ = parse_dot(dot)
        self.assertEqual(labels["a"], 'Line\nTwo "Q"')

    def test_parse_rejects_subgraph(self):
        with self.assertRaises(ValueError):
            parse_dot("digraph G {\nsubgraph cluster_0 {\n}\n}")


class InferConditionTests(unittest.TestCase):
    def test_infer_has(self):
        condition = infer_condition_from_label("HER2+")
        self.assertTrue(condition(Data(("HER2+",))))
        self.assertFalse(condition(Data(("HR+",))))

    def test_infer_has_any(self):
        condition = infer_condition_from_label("T1a or T1b")
        self.assertTrue(condition(Data(("T1a",))))
        self.assertTrue(condition(Data(("T1b",))))
        self.assertFalse(condition(Data(("T2",))))

    def test_infer_has_all(self):
        condition = infer_condition_from_label("HR+/HER2-")
        self.assertTrue(condition(Data(("HR+", "HER2-"))))
        self.assertFalse(condition(Data(("HR+",))))


class BuildGraphTests(unittest.TestCase):
    def test_find_roots(self):
        roots = find_roots({"a", "b", "c"}, [("a", "b")], node_order=["c", "a", "b"])
        self.assertEqual(roots, ["c", "a"])

    def test_single_child_remains_unconditional(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="Child"];
          a -> b;
        }
        '''
        graph = dot_to_graph(dot)
        self.assertEqual(walk(graph, Data(set())), [["Root", "Child"]])

    def test_branch_children_get_conditions(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="HR+/HER2-"];
          a -> b;
          a -> c;
        }
        '''
        graph = dot_to_graph(dot)
        self.assertEqual(walk(graph, Data(("HER2+",))), [["Root", "HER2+"]])
        self.assertEqual(walk(graph, Data(("HR+", "HER2-"))), [["Root", "HR+/HER2-"]])
        self.assertEqual(walk(graph, Data(("HER2-",))), [["Root"]])

    def test_child_order_follows_edge_order(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="B"];
          c [label="C"];
          a -> c;
          a -> b;
        }
        '''
        graph = dot_to_graph(dot)
        self.assertEqual([child.label for child in graph.children], ["C", "B"])

    def test_build_graph_multiple_roots_returns_list(self):
        graph = build_graph({"a": "A", "b": "B"}, [], node_order=["b", "a"])
        self.assertIsInstance(graph, list)
        self.assertEqual([n.label for n in graph], ["B", "A"])

    def test_dot_to_graph_wraps_multiple_roots(self):
        graph = dot_to_graph('''
        digraph G {
          a [label="A"];
          b [label="B"];
        }
        ''')
        self.assertEqual(graph.label, "root")
        self.assertEqual(sorted(child.label for child in graph.children), ["A", "B"])

    def test_cycle_returns_synthetic_root(self):
        dot = '''
        digraph G {
          a [label="A"];
          b [label="B"];
          a -> b;
          b -> a;
        }
        '''
        graph = dot_to_graph(dot)
        self.assertEqual(graph.label, "root")
        self.assertEqual(sorted(child.label for child in graph.children), ["A", "B"])

    def test_schema_inference_on_dot_graph(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="HR+/HER2-"];
          a -> b;
          a -> c;
        }
        '''
        graph = dot_to_graph(dot)
        schema = infer_schema(graph)
        self.assertIn("attr", schema)
        self.assertIn("contains_all", schema["attr"]["ops"])
        self.assertIn("contains_any", schema["attr"]["ops"])

    def test_shared_child_is_cloned_per_incoming_edge(self):
        dot = '''
        digraph G {
          p1 [label="P1"];
          p2 [label="P2"];
          c [label="HER2+"];
          p1 -> c;
          p1 -> x;
          p2 -> c;
          p2 -> y;
          x [label="X"];
          y [label="Y"];
        }
        '''
        forest = dot_to_forest(dot)
        p1, p2 = forest.roots
        self.assertIsNot(p1.children[0], p2.children[0])
        self.assertTrue(p1.children[0].condition(Data(("HER2+",))))
        self.assertTrue(p2.children[0].condition(Data(("HER2+",))))

    def test_analyze_dot_graph_reports_graph_properties(self):
        result = parse_dot_with_metadata('''
        digraph G {
          a [label="X"];
          b [label="X"];
          c [label="C"];
          a -> c;
          b -> c;
        }
        ''')
        analysis = analyze_dot_graph(result.node_labels, result.edges, node_order=result.node_order)
        self.assertEqual(analysis.roots, ["a", "b"])
        self.assertEqual(analysis.shared_nodes, ["c"])
        self.assertEqual(analysis.duplicate_labels, {"X": ["a", "b"]})
        self.assertTrue(analysis.synthetic_root_required)


class EbcSmokeTests(unittest.TestCase):
    def test_parse_ebc_dot(self):
        with open("data/dot/ebc.dot", "r", encoding="utf-8") as f:
            graph = dot_to_graph(f.read())
        self.assertEqual(graph.label, "root")
        self.assertTrue(any(child.label == "Overview of EBC treatment" for child in graph.children))

        overview = next(child for child in graph.children if child.label == "Overview of EBC treatment")
        self.assertTrue(any(child.label == "All HR+" for child in overview.children))
        self.assertTrue(any(child.label == "HER2+_a" for child in overview.children))


if __name__ == "__main__":
    unittest.main()
