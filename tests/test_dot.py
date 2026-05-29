import unittest

from dgraph.dot.analyze import analyze_dot_graph, find_roots
from dgraph.dot.interpret import build_graph, dot_to_forest, dot_to_graph
from dgraph.dot.ir import dot_to_ir
from dgraph.dot.parse import parse_dot, parse_dot_with_metadata
from dgraph.dot.reuse import plan_source_reuse
from dgraph.dot.compile import collect_imports, dot_parsed_to_dg, dot_to_dg
from dgraph.graph import Data, walk
from dgraph.logic import infer_condition
from dgraph.schema import infer_schema


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

    def test_parse_single_line_graph(self):
        dot = 'digraph G { a [label="A"]; b [label="B"]; a -> b; }'
        labels, edges = parse_dot(dot)
        self.assertEqual(labels, {"a": "A", "b": "B"})
        self.assertEqual(edges, [("a", "b")])

    def test_parse_label_unescapes_common_sequences(self):
        dot = r'''
        digraph G {
          a [label="Line\nTwo \"Q\""];
        }
        '''
        labels, _ = parse_dot(dot)
        self.assertEqual(labels["a"], 'Line\nTwo "Q"')

    def test_parse_ignores_unsupported_syntax(self):
        dot = '''
        digraph G {
          subgraph cluster_0 {
          }
          a [label="A"];
          b [label="B"];
          a -> b [style=dashed];
          a:out -> b;
          a -- b;
        }
        '''
        labels, edges = parse_dot(dot)
        self.assertEqual(labels, {"a": "A", "b": "B"})
        self.assertEqual(edges, [])


class InferConditionTests(unittest.TestCase):
    def test_infer_has(self):
        condition = infer_condition("HER2+")
        self.assertTrue(condition(Data(("HER2+",))))
        self.assertFalse(condition(Data(("HR+",))))

    def test_infer_has_any(self):
        condition = infer_condition("T1a or T1b")
        self.assertTrue(condition(Data(("T1a",))))
        self.assertTrue(condition(Data(("T1b",))))
        self.assertFalse(condition(Data(("T2",))))

    def test_infer_implicit_and_and_line_or(self):
        condition = infer_condition("cT1b N0\nHER2+")
        self.assertTrue(condition(Data(("cT1b", "N0"))))
        self.assertTrue(condition(Data(("HER2+",))))
        self.assertFalse(condition(Data(("cT1b",))))

    def test_infer_has_all_from_and(self):
        condition = infer_condition("ofs and postmenopausal")
        self.assertTrue(condition(Data(("ofs", "postmenopausal"))))
        self.assertFalse(condition(Data(("ofs",))))


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
        self.assertEqual(walk(graph, Data(set())), ([['Root', 'Child']], []))

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
        self.assertEqual(walk(graph, Data(("HER2+",))), ([['Root', 'HER2+']], []))
        self.assertEqual(walk(graph, Data(("HR+/HER2-",))), ([['Root', 'HR+/HER2-']], []))
        self.assertEqual(walk(graph, Data(("HER2-"))), ([['Root']], ['HER2+', 'HR+/HER2-']))

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
        self.assertEqual(schema["HER2+"], "tag")
        self.assertEqual(schema["HR+/HER2-"], "tag")

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
    def test_dot_to_dg_ignores_unsupported_edge_attributes(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="Leaf"];
          a -> b [style=dashed];
        }
        '''
        source = dot_to_dg(dot)
        self.assertIn("node('Root')", source)
        self.assertIn("node('Leaf')", source)

    def test_dot_to_dg_emits_dsl_calls(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="Leaf"];
          a -> b;
          b -> c;
        }
        '''
        source = dot_to_dg(dot)
        self.assertIn("from dgraph.graph import branch, chain, node", source)
        self.assertNotIn("from dgraph.condition", source)
        self.assertIn("graph = chain('Root', 'HER2+', 'Leaf')", source)

    def test_dot_to_dg_emits_branch_conditions(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="HR+/HER2-"];
          d [label="premenopausal patients receiving ofs and postmenopausal patients"];
          a -> b;
          a -> c;
          a -> d;
        }
        '''
        source = dot_to_dg(dot)
        self.assertIn("from dgraph.condition import all_of, has", source)
        self.assertIn("branch(\n        'HER2+',\n        has('HER2+')", source)
        self.assertIn("branch(\n        'HR+/HER2-',\n        has('HR+/HER2-')", source)
        self.assertIn("all_of", source)
        self.assertIn("has('premenopausal')", source)
        self.assertIn("has('postmenopausal')", source)

    def test_dot_to_dg_emits_implicit_logic_conditions(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="cT1b N0"];
          c [label="HER2+"];
          a -> b;
          a -> c;
        }
        '''
        source = dot_to_dg(dot)
        self.assertIn("from dgraph.condition import all_of, has", source)
        self.assertIn("all_of(has('cT1b'), has('N0'))", source)

    def test_dot_to_dg_hoists_repeated_chains(self):
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
        source = dot_to_dg(dot)
        self.assertIn("shared = chain('Shared 1', 'Shared 2', 'Shared 3')", source)
        self.assertIn("branch(\n        'Left',\n        has('Left')", source)
        self.assertIn("branch(\n        'Right',\n        has('Right')", source)

    def test_dot_to_dg_hoists_repeated_subtrees(self):
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
        source = dot_to_dg(dot)
        self.assertIn("choice = node(", source)
        self.assertIn("'Choice'", source)
        self.assertNotIn("x = node('X')", source)
        self.assertNotIn("y = node('Y')", source)
        self.assertEqual(source.count("choice"), 3)
        self.assertIn("graph = node(", source)

    def test_dot_to_dg_hoists_shared_terminals_across_aliased_subgraphs(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="Left"];
          c [label="Right"];
          d [label="Choice 1"];
          e [label="Choice 2"];
          f [label="ALND [II, A]"];
          g [label="RT (axilla) [II, B]"];
          a -> b;
          a -> c;
          b -> d;
          c -> e;
          d -> f;
          d -> g;
          e -> f;
          e -> g;
        }
        '''
        source = dot_to_dg(dot)
        self.assertNotIn("choice_1 = node(", source)
        self.assertNotIn("choice_2 = node(", source)
        self.assertIn("alnd = node('ALND [II, A]')", source)
        self.assertIn("rt = node('RT (axilla) [II, B]')", source)
        self.assertEqual(source.count("alnd"), 3)
        self.assertIn("\n            rt\n", source)

    def test_dot_to_dg_indents_multiline_children(self):
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
        source = dot_to_dg(dot)
        self.assertIn("\n    node(\n", source)
        self.assertIn("node('X')", source)
        self.assertIn("node('Y')", source)

    def test_dot_to_dg_keeps_terminal_nodes_structural(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="AMAROS criteria met"];
          c [label="RT (axilla) [II, B]"];
          d [label="ALND [II, A]"];
          a -> b;
          b -> c;
          b -> d;
        }
        '''
        source = dot_to_dg(dot)
        self.assertIn("node(\n        'AMAROS criteria met'", source)
        self.assertIn("node('RT (axilla) [II, B]')", source)
        self.assertIn("node('ALND [II, A]')", source)
        self.assertNotIn("branch(\n            'RT (axilla) [II, B]'", source)
        self.assertNotIn("branch(\n            'ALND [II, A]'", source)

    def test_dot_to_dg_does_not_duplicate_branch_parent_node(self):
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
        source = dot_to_dg(dot)
        self.assertIn("node(\n        'HER2+'", source)
        self.assertNotIn("branch(\n            'HER2+'", source)
        self.assertNotIn("node(\n        ''", source)

    def test_dot_parsed_to_dg_accepts_metadata(self):
        parsed = parse_dot_with_metadata('''
        digraph G {
          a [label="A"];
        }
        ''')
        source = dot_parsed_to_dg(parsed)
        self.assertIn("graph = node('A')", source)


class ReusePlanningTests(unittest.TestCase):
    def test_plan_source_reuse_exposes_selected_aliases(self):
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
        plan = plan_source_reuse(dot_to_ir(dot))
        self.assertIn("choice", set(plan.aliases.values()))

    def test_collect_imports_only_includes_used_condition_helpers(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          a -> b;
        }
        '''
        imports = collect_imports(dot_to_ir(dot))
        self.assertEqual(imports.condition_helpers, ())

    def test_short_name_disambiguation_uses_more_words_as_needed(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="Left"];
          c [label="Right"];
          d [label="RT (axilla) [II, B]"];
          e [label="RT (basis axilla) [II, B]"];
          f [label="Choice 1"];
          g [label="Choice 2"];
          a -> b;
          a -> c;
          b -> f;
          c -> g;
          f -> d;
          f -> e;
          g -> d;
          g -> e;
        }
        '''
        source = dot_to_dg(dot)
        self.assertIn("rt = node('RT (axilla) [II, B]')", source)
        self.assertIn("rt_basis = node('RT (basis axilla) [II, B]')", source)


class EquivalenceTests(unittest.TestCase):
    def _assert_equivalent_graphs(self, dot: str, cases: list[Data]) -> None:
        graph1 = dot_to_graph(dot)
        ns: dict[str, object] = {}
        exec(dot_to_dg(dot), ns, ns)
        graph2 = ns["graph"]

        self.assertEqual(infer_schema(graph1), infer_schema(graph2))
        for x in cases:
            self.assertEqual(walk(graph1, x), walk(graph2, x))

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
        self._assert_equivalent_graphs(
            dot,
            [
                Data(("HER2+",)),
                Data(("HR+/HER2-",)),
            ],
        )

    def test_dot_to_graph_matches_emitted_source_for_and_conditions(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="premenopausal patients receiving ofs and postmenopausal patients"];
          c [label="Leaf"];
          a -> b;
          b -> c;
        }
        '''
        self._assert_equivalent_graphs(
            dot,
            [
                Data(set()),
                Data(("premenopausal patients receiving ofs",)),
                Data(("postmenopausal patients",)),
                Data(("premenopausal patients receiving ofs", "postmenopausal patients")),
            ],
        )

    def test_dot_to_graph_matches_emitted_source_for_nested_branches(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="HER2+"];
          c [label="CT1 N0"];
          d [label=">=cT2 or cN+"];
          e [label="Systemic treatment"];
          a -> b;
          b -> c;
          b -> d;
          c -> e;
          d -> e;
        }
        '''
        self._assert_equivalent_graphs(
            dot,
            [
                Data(("HER2+", "CT1 N0")),
                Data(("HER2+", ">=cT2")),
                Data(("HER2+", "cN+")),
            ],
        )

    def test_terminal_nodes_are_not_branch_nodes_in_runtime_graph(self):
        dot = '''
        digraph G {
          a [label="Root"];
          b [label="AMAROS criteria met"];
          c [label="RT (axilla) [II, B]"];
          d [label="ALND [II, A]"];
          a -> b;
          b -> c;
          b -> d;
        }
        '''
        graph = dot_to_graph(dot)
        amaros = graph.children[0]
        self.assertEqual(amaros.label, "AMAROS criteria met")
        self.assertTrue(all(child.condition(True) for child in amaros.children))
        self.assertEqual([getattr(child.condition, 'attrs', ()) for child in amaros.children], [(), ()])
        self.assertEqual([child.label for child in amaros.children], ["RT (axilla) [II, B]", "ALND [II, A]"])

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
        self.assertEqual(walk(graph, Data(("HER2+",))), ([['Root', 'HER2+']], []))


class EbcSmokeTests(unittest.TestCase):
    def test_parse_ebc_dot(self):
        dot = '''
        digraph G {
          rankdir=TB;

          r  [label="Overview of EBC treatment", shape=box];

          a1 [label="HR+", shape=box];
          t1 [label="ET [I, A]", shape=box];

          a3 [label="HR+/HER2-", shape=box];
          a4 [label="HER2+", shape=box];

          r -> a1;
          r -> a3;
          r -> a4;

          a1 -> t1;
        }
        '''
        graph = dot_to_graph(dot)
        self.assertEqual(graph.label, "Overview of EBC treatment")
        self.assertTrue(any(child.label == "HR+" for child in graph.children))
        self.assertTrue(any(child.label == "HER2+" for child in graph.children))


if __name__ == "__main__":
    unittest.main()
