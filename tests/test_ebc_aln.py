from dataclasses import dataclass
import unittest

import dgraph.condition as dc
import dgraph.graph as dg
from dgraph.graph import branch, case, match, node, walk
from dgraph.schema import infer_schema, validate_data


@dataclass
class Data(dg.Data):
    positive_nodes: int


rt_ba = node("RT (basis axilla) [II, B]")
rt_a = node("RT (axilla) [II, B]")
alnd_local = node("ALND [II, A]")
alnd_regional = node("ALND (or RT) of regional LNs [II, B]")

sln_neg = branch(
    "SLN-",
    dc.has("SLN-"),
    node("No further locoregional treatment"),
)

bottom_branches = (
    branch("ACOSOG-Z0011 criteria met", dc.has("ACOSOG-Z0011+"), rt_ba),
    branch("AMAROS critiera met", dc.has("AMAROS+"), rt_a, alnd_local),
    branch(
        "ACOSOG-Z0011 criteria not met or >2 positive LNs",
        dc.all_of(dc.has("ACOSOG-Z0011-"), dc.gt("positive_nodes", 2)),
        alnd_local,
    ),
)

slnb = node(
    "SLNB [I, A]",
    sln_neg,
    branch("SLN+", dc.has("SLN+"), bottom_branches),
)

biopsy = node(
    "Biopsy",
    match(
        "tags",
        case("pNX", slnb),
        case("pN+", bottom_branches),
    ),
)

surgery_indicated = branch(
    "primary surgery indicated",
    dc.has("primary_surgery"),
    match(
        "tags",
        case(("N0", "cN0", "iN0"), node("SLNB [I, A]", slnb.children), label="cN0/iN0"),
        case(("N+", "cN+", "iN+"), biopsy, label="cN+/iN+"),
    ),
)

neoadjuvant_therapy = node(
    "Follow Figures 4-7 for neoadjuvant therapy",
    branch(
        "ycN0/ypN0 after neoadjuvant ChT",
        dc.has_any("ycN0", "ypN0"),
        branch(
            "SLN- or TAD-",
            dc.has_any("SLN-", "TAD-"),
            node("Consider RT if pN+ at primary diagnosis [II, B]"),
        ),
        branch(
            "SLN+ or TAD+",
            dc.has_any("SLN+", "TAD+"),
            alnd_regional,
        ),
    ),
    branch(
        "ycN+/ypN+ after neoadjuvant ChT",
        dc.has_any("ycN+", "ypN+"),
        alnd_regional,
    ),
)

neoadjuvant_indicated = branch(
    "PST indicated",
    dc.has("neoadjuvant"),
    branch("cN0/pN0 at primary diagnosis", dc.has_any("cN0", "pN0"), neoadjuvant_therapy),
    branch("cN+/pN+ at primary diagnosis", dc.has_any("cN+", "pN+"), neoadjuvant_therapy),
)

graph = node(
    "EBC-ALN",
    surgery_indicated,
    neoadjuvant_indicated,
)


class EbcAlnSchemaTests(unittest.TestCase):
    def test_infer_schema_matches_demo(self):
        schema = infer_schema(graph)
        self.assertEqual(
            schema,
            {
                "primary_surgery": "tag",
                "N0": "tag",
                "cN0": "tag",
                "iN0": "tag",
                "SLN-": "tag",
                "SLN+": "tag",
                "ACOSOG-Z0011+": "tag",
                "AMAROS+": "tag",
                "ACOSOG-Z0011-": "unknown",
                "positive_nodes": "unknown",
                "N+": "tag",
                "cN+": "tag",
                "iN+": "tag",
                "pNX": "tag",
                "pN+": "tag",
                "neoadjuvant": "tag",
                "pN0": "tag",
                "ycN0": "tag",
                "ypN0": "tag",
                "TAD-": "tag",
                "TAD+": "tag",
                "ycN+": "tag",
                "ypN+": "tag",
            },
        )


class EbcAlnWalkExamplesTest(unittest.TestCase):
    def test_example_1_primary_surgery_in_plus_stops_at_biopsy(self):
        x = Data(("primary_surgery", "iN+"), positive_nodes=3)
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [["EBC-ALN", "primary surgery indicated", "cN+/iN+", "Biopsy"]],
                [("pNX",), ("pN+",)],
            ),
        )

    def test_example_2_primary_surgery_pn_plus_acosog(self):
        x = Data(("primary_surgery", "cN+", "pN+", "ACOSOG-Z0011+"), positive_nodes=1)
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    "EBC-ALN",
                    "primary surgery indicated",
                    "cN+/iN+",
                    "Biopsy",
                    "pN+",
                    "ACOSOG-Z0011 criteria met",
                    "RT (basis axilla) [II, B]",
                ]],
                [],
            ),
        )

    def test_example_3_primary_surgery_pn_plus_amaros(self):
        x = Data(("primary_surgery", "cN+", "pN+", "AMAROS+"), positive_nodes=1)
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [
                    [
                        "EBC-ALN",
                        "primary surgery indicated",
                        "cN+/iN+",
                        "Biopsy",
                        "pN+",
                        "AMAROS critiera met",
                        "RT (axilla) [II, B]",
                    ],
                    [
                        "EBC-ALN",
                        "primary surgery indicated",
                        "cN+/iN+",
                        "Biopsy",
                        "pN+",
                        "AMAROS critiera met",
                        "ALND [II, A]",
                    ],
                ],
                [],
            ),
        )

    def test_example_4_neoadjuvant_cn0_stops_at_follow_up_figure(self):
        x = Data(("neoadjuvant", "cN0"), positive_nodes=0)
        self.assertEqual(validate_data(infer_schema(graph), x), [])
        self.assertEqual(
            walk(graph, x),
            (
                [[
                    "EBC-ALN",
                    "PST indicated",
                    "cN0/pN0 at primary diagnosis",
                    "Follow Figures 4-7 for neoadjuvant therapy",
                ]],
                [("ycN0", "ypN0"), ("ycN+", "ypN+")],
            ),
        )


if __name__ == "__main__":
    unittest.main()
