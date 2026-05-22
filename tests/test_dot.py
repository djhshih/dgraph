import unittest

from dgraph.dot import analyze_dot_graph, build_graph, dot_parsed_to_source, dot_to_forest, dot_to_graph, dot_to_source, find_roots, infer_condition_from_label, parse_dot, parse_dot_with_metadata
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

    def test_single_child_becomes_chain(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="Child"];
          a -> b;
        }
        '''
        graph = dot_to_graph(dot)
        self.assertEqual(graph.label, "Root")
        self.assertEqual([child.label for child in graph.children], ["Child"])
        self.assertEqual(walk(graph, Data(set())), [["Root", "Child"]])

    def test_branch_children_become_dsl_branches(self):
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
        self.assertEqual([child.label for child in graph.children], ["HER2+", "HR+/HER2-"])
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
        self.assertEqual(schema["attr"]["kind"], "tag")

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
        self.assertEqual(p1.children[0].children, [])
        self.assertEqual(p2.children[0].children, [])

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


class SourceEmissionTests(unittest.TestCase):
    def test_dot_to_source_emits_dsl_calls(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="Leaf"];
          a -> b;
          b -> c;
        }
        '''
        source = dot_to_source(dot)
        self.assertIn("from dgraph.graph import branch, chain, node", source)
        self.assertIn("import dgraph.condition as dc", source)
        self.assertIn("graph = chain('Root', 'HER2+', 'Leaf')", source)

    def test_dot_to_source_emits_branch_conditions(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="HR+/HER2-"];
          a -> b;
          a -> c;
        }
        '''
        source = dot_to_source(dot)
        self.assertIn("branch(\n        'HER2+',\n        dc.has('HER2+')", source)
        self.assertIn("branch(\n        'HR+/HER2-',\n        dc.has_all('HR+', 'HER2-')", source)

    def test_dot_to_source_hoists_repeated_chains(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="Left"];
          c [label="Right"];
          d [label="Shared 1"];
          e [label="Shared 2"];
          f [label="Shared 3"];
          a -> b;
          a -> c;
          b -> d;
          c -> d;
          d -> e;
          e -> f;
        }
        '''
        source = dot_to_source(dot)
        self.assertIn("shared_1_shared_2_shared_3 = chain('Shared 1', 'Shared 2', 'Shared 3')", source)
        self.assertIn("branch(\n        'Left',\n        dc.has('Left')", source)
        self.assertIn("branch(\n        'Right',\n        dc.has('Right')", source)
        self.assertIn("shared_1_shared_2_shared_3", source)

    def test_dot_to_source_hoists_repeated_subtrees(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="Left"];
          c [label="Right"];
          d [label="Choice"];
          e [label="X"];
          f [label="Y"];
          a -> b;
          a -> c;
          b -> d;
          c -> d;
          d -> e;
          d -> f;
        }
        '''
        source = dot_to_source(dot)
        self.assertIn("choice = node(", source)
        self.assertNotIn("x = node('X')", source)
        self.assertNotIn("y = node('Y')", source)
        self.assertIn("graph = node(", source)

    def test_dot_to_source_indents_multiline_children(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="Parent"];
          c [label="X"];
          d [label="Y"];
          a -> b;
          b -> c;
          b -> d;
        }
        '''
        source = dot_to_source(dot)
        self.assertIn("\n    node(\n", source)
        self.assertIn("\n        branch(\n", source)

    def test_dot_to_source_does_not_duplicate_branch_parent_node(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="CT1 N0"];
          d [label=">=cT2 or cN+"];
          a -> b;
          b -> c;
          b -> d;
        }
        '''
        source = dot_to_source(dot)
        self.assertIn("node(\n        'HER2+'", source)
        self.assertNotIn("branch(\n            'HER2+'", source)
        self.assertNotIn("node(\n        ''", source)

    def test_dot_parsed_to_source_accepts_metadata(self):
        parsed = parse_dot_with_metadata('''
        digraph G {
          a [label="A"];
        }
        ''')
        source = dot_parsed_to_source(parsed)
        self.assertIn("graph = node('A')", source)


class EquivalenceTests(unittest.TestCase):
    def test_dot_to_graph_matches_emitted_source_behavior(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="HR+/HER2-"];
          d [label="Leaf"];
          a -> b;
          a -> c;
          b -> d;
          c -> d;
        }
        '''
        graph1 = dot_to_graph(dot)
        ns: dict[str, object] = {}
        exec(dot_to_source(dot), ns, ns)
        graph2 = ns["graph"]

        cases = [
            Data(set()),
            Data(("HER2+",)),
            Data(("HR+", "HER2-")),
            Data(("HER2-",)),
        ]
        for x in cases:
            self.assertEqual(walk(graph1, x), walk(graph2, x))

    def test_branch_node_not_duplicated_in_runtime_graph(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          a -> b;
        }
        '''
        graph = dot_to_graph(dot)
        self.assertEqual([child.label for child in graph.children], ["HER2+"])
        self.assertEqual(graph.children[0].children, [])
        self.assertEqual(walk(graph, Data(("HER2+",))), [["Root", "HER2+"]])


class EbcSmokeTests(unittest.TestCase):
    def test_parse_ebc_dot(self):
        with open("data/dot/ebc.dot", "r", encoding="utf-8") as f:
            graph = dot_to_graph(f.read())
        self.assertEqual(graph.label, "Overview of EBC treatment")

        overview = graph
        self.assertTrue(any(child.label == "All HR+" for child in overview.children))
        self.assertTrue(any(child.label == "HER2+" for child in overview.children))


if __name__ == "__main__":
    unittest.main()
