import rdflib
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_populado_1m.owl")

g = rdflib.Graph()
g.parse(DATA_PATH, format="xml")

# Find a movie
find_movie_query = """
PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
SELECT DISTINCT ?movie WHERE {
  ?movie rdf:type :Movie .
} LIMIT 5
"""
movies = [row.movie for row in g.query(find_movie_query)]
print("Found movies:", movies)

for movie in movies:
    print(f"\n--- Triples for movie: {movie} ---")
    for s, p, o in g.triples((movie, None, None)):
        print(f"  {p} -> {o}")
        
    # Also find who plays roles in this movie
    roles_query = f"""
    PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
    SELECT ?person ?name ?role_type WHERE {{
      <{movie}> :contains_role ?role .
      ?role rdf:type ?role_type .
      ?person :has_role ?role .
      OPTIONAL {{ ?person :has_name ?name }}
    }}
    """
    print("  Roles / People in this movie:")
    for row in g.query(roles_query):
        print(f"    Person: {row.person} ({row.name}), Role Type: {row.role_type}")
