import rdflib
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_populado_1m.owl")

g = rdflib.Graph()
g.parse(DATA_PATH, format="xml")

# Find movies with their title and genres and directors/actors
query = """
PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
SELECT DISTINCT ?movie ?title WHERE {
  ?movie rdf:type :Movie .
  ?movie :has_title ?title .
  ?role :is_played_in ?movie .
} LIMIT 5
"""

for row in g.query(query):
    movie = row.movie
    title = row.title
    print(f"\nMovie: {movie} ({title})")
    
    # Genres
    genres = []
    for s, p, o in g.triples((movie, rdflib.URIRef("http://www.semanticweb.org/ontologies/2026/3/MOREO#has_genre"), None)):
        genres.append(o.split("#")[-1])
    print("  Genres:", genres)
    
    # Roles
    roles_query = f"""
    PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
    SELECT DISTINCT ?name ?role_type WHERE {{
      ?role :is_played_in <{movie}> .
      ?role rdf:type ?role_type .
      ?person :has_role ?role .
      ?person :has_name ?name .
    }}
    """
    for r_row in g.query(roles_query):
        role_name = r_row.role_type.split("#")[-1]
        print(f"  {role_name}: {r_row.name}")
