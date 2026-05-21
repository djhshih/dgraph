import unittest

import dgraph.condition as dc
from dgraph.dot import build_graph, dot_to_graph, find_roots, infer_condition_from_label, parse_dot
from dgraph.graph import Data, walk


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
        roots = find_roots({"a", "b", "c"}, [("a", "b")])
        self.assertEqual(roots, ["a", "c"])

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
        graph = build_graph({"a": "A", "b": "B"}, [])
        self.assertIsInstance(graph, list)
        self.assertEqual(sorted(n.label for n in graph), ["A", "B"])

    def test_dot_to_graph_wraps_multiple_roots(self):
        graph = dot_to_graph('''
        digraph G {
          a [label="A"];
          b [label="B"];
        }
        ''')
        self.assertEqual(graph.label, "DOT")
        self.assertEqual(sorted(child.label for child in graph.children), ["A", "B"])

    def test_cycle_raises(self):
        dot = '''
        digraph G {
          a [label="A"];
          b [label="B"];
          a -> b;
          b -> a;
        }
        '''
        with self.assertRaises(ValueError):
            dot_to_graph(dot)


class EbcSmokeTests(unittest.TestCase):
    def test_parse_ebc_dot(self):
        with open("data/dot/ebc.dot", "r", encoding="utf-8") as f:
            graph = dot_to_graph(f.read())
        self.assertEqual(graph.label, "DOT")
        self.assertTrue(any(child.label == "Overview of EBC treatment" for child in graph.children))

        overview = next(child for child in graph.children if child.label == "Overview of EBC treatment")
        self.assertTrue(any(child.label == "All HR+" for child in overview.children))
        self.assertTrue(any(child.label == "HER2+_a" for child in overview.children))


if __name__ == "__main__":
    unittest.main()
