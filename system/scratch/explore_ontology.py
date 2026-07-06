import rdflib
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_populado_completo.owl")

g = rdflib.Graph()
g.parse(DATA_PATH, format="xml")

print("Graph size:", len(g))

# 1. Get classes
classes_query = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?c WHERE {
  ?c rdf:type owl:Class .
} LIMIT 20
"""
print("\nSome Classes:")
for row in g.query(classes_query):
    print(row.c)

# 2. Get some awards
awards_query = """
PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
SELECT DISTINCT ?award WHERE {
  ?award rdf:type :Award .
} LIMIT 10
"""
print("\nSome Awards:")
for row in g.query(awards_query):
    print(row.award)

# 3. Get some film genres
genres_query = """
PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
SELECT DISTINCT ?genre WHERE {
  ?genre rdf:type ?type .
  ?type rdfs:subClassOf* :FilmGenre .
} LIMIT 10
"""
print("\nSome Genres (subclasses of FilmGenre):")
for row in g.query(genres_query):
    print(row.genre)

# 4. Get some actors and directors
people_query = """
PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
SELECT DISTINCT ?person ?role_type WHERE {
  ?person rdf:type :Person .
  ?person :has_role ?role .
  ?role rdf:type ?role_type .
  FILTER(?role_type IN (:ActorRole, :DirectorRole))
} LIMIT 20
"""
print("\nPeople with Actor/Director Roles:")
for row in g.query(people_query):
    print(row.person, row.role_type)
