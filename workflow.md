# Workflow

1. Download image from website.
2. Extract graph from image and write in DOT format (external service).
3. Parse DOT file (`dgraph.dot`) and construct decision graph (`dgraph.graph`).
4. Walk through decision graph with patient data to return all viable paths.

