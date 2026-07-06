import rdflib
from pyshacl import validate

def validate_ontology(data_graph_path: str, shacl_path: str) -> tuple[bool, str]:
    print(f"[SHACL] Loading data graph from {data_graph_path}...")
    g = rdflib.Graph()
    if data_graph_path.endswith(".ttl"):
        g.parse(data_graph_path, format="ttl")
    else:
        g.parse(data_graph_path, format="xml")
    print(f"[SHACL] Data graph loaded. Found {len(g)} triples.")
    
    print(f"[SHACL] Loading SHACL shapes from {shacl_path}...")
    sh_g = rdflib.Graph()
    sh_g.parse(shacl_path, format="ttl")
    print(f"[SHACL] SHACL shapes loaded. Found {len(sh_g)} triples.")
    
    print(f"[SHACL] Executing PySHACL validation (with RDFS inference)...")
    conforms, results_graph, results_text = validate(
        g,
        shacl_graph=sh_g,
        ont_graph=None,
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        debug=False
    )
    print(f"[SHACL] Validation completed. Conforms: {conforms}")
    return conforms, results_text
