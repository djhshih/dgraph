# Early breast cancer diagnosis and staging overview
# Built from data/dot/ebc-dx.dot

from pathlib import Path

import dgraph.graph as dg
from dgraph.dot import dot_to_graph, dot_to_source
from dgraph.graph import Data

_DOT_PATH = Path(__file__).resolve().parents[3] / "data" / "dot" / "ebc.dot"

dot_text = _DOT_PATH.read_text()
print(dot_to_source(dot_text))
