# Workflow

Each subdir in `data` contains the decision tree for one set of guidelines.

1. Download image from website to `data/*/img`.
2. Extract graph from image and write in DOT format (external service) to
   `data/*/dot`. Generate pdf and ensure correctness. Commit the dot file.
4. Run `bin/dot2dg.py` to generate Python code for constructing the decision
   graph from the dot file in `data/*/dg`.
4. Prepare patient data in `data/patient`.
5. In Python, run `dgraph.graph.walk(graph, data)` to walk through a decision 
   graph with patient data to return all viable paths.

