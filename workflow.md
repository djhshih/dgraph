# Workflow

1. Download image from website to `data/img`.
2. Extract graph from image and write in DOT format (external service) to
   `data/raw`.
3. Simplify and optimize dot file manually, write to `data/dot`.
3. Parse DOT file (`dgraph.dot`) and construct decision graph (`dgraph.graph`),
   writing to `data/graph`.
4. Prepare patient data in `data/patient`.
5. Walk through decision graph with patient data to return all viable paths.

