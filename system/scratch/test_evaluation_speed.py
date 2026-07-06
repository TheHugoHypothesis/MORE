import os
import time
import rdflib
import torch
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_populado_1m.owl")

print("Loading graph...")
start = time.time()
g = rdflib.Graph()
g.parse(DATA_PATH, format="xml")
print(f"Graph loaded in {time.time() - start:.2f} seconds. Total triples: {len(g)}")

moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
rdf = rdflib.RDF

print("Loading checkpoint...")
ckpt = torch.load(os.path.join(PROJECT_ROOT, "models", "model.pt"))
test_gt = ckpt["test_ground_truth"]
print(f"Test ground truth has {len(test_gt)} users.")

print("Pre-computing static recommendation data...")
start_pre = time.time()
static_recs = set()

# Helper to check if a URI represents a Movie
def is_movie(m):
    for t in g.objects(m, rdf.type):
        t_str = str(t)
        if "Movie" in t_str or "Documentary" in t_str or "FictionMovie" in t_str:
            return True
    return False

# 1. Global Rating > 4.5
for gr in g.subjects(rdf.type, moreo.GlobalRating):
    score_lit = g.value(gr, moreo.has_average_score)
    try:
        if score_lit and float(score_lit) > 4.5:
            for m in g.objects(gr, moreo.is_global_rating_quality_of):
                if is_movie(m):
                    static_recs.add(str(m))
    except (ValueError, TypeError):
        pass

# 4. Recomendação de filme anual (2026)
for role_type in [moreo.Role, moreo.DirectorRole, moreo.ActorRole, moreo.WriterRole, moreo.ProducerRole]:
    for role in g.subjects(rdf.type, role_type):
        m = g.value(role, moreo.is_played_in)
        if m and is_movie(m):
            for award in g.subjects(moreo.is_award_of, role):
                date_lit = g.value(award, moreo.has_award_date)
                if date_lit and "2026" in str(date_lit):
                    static_recs.add(str(m))
                    break

# Index movie nationalities
movie_nationalities = defaultdict(set)
for movie_type in [moreo.Movie, moreo.FictionMovie, moreo.Documentary]:
    for m in g.subjects(rdf.type, movie_type):
        for n in g.objects(m, moreo.has_nationality):
            movie_nationalities[str(n)].add(str(m))

# Index person roles -> movies
person_movies = defaultdict(set)
for role_type in [moreo.Role, moreo.DirectorRole, moreo.ActorRole, moreo.WriterRole, moreo.ProducerRole]:
    for role in g.subjects(rdf.type, role_type):
        m = g.value(role, moreo.is_played_in)
        if m and is_movie(m):
            for person in g.subjects(moreo.has_role, role):
                person_movies[str(person)].add(str(m))

# Index award -> movies
award_movies = defaultdict(set)
for award in g.subjects(rdf.type, moreo.Award):
    for m in g.objects(award, moreo.is_award_of):
        if is_movie(m):
            award_movies[str(award)].add(str(m))

# Pre-compute user ratings counts
user_ratings_count = defaultdict(int)
for s, p, o in g.triples((None, moreo.performs_rating, None)):
    user_ratings_count[str(s)] += 1

print(f"Pre-computation completed in {time.time() - start_pre:.4f} seconds.")
print(f"Static recommendations: {len(static_recs)}")

print("Running fast evaluation loop...")
start_loop = time.time()
all_recommendations = {}

for user_uri_str in test_gt.keys():
    user_uri = rdflib.URIRef(user_uri_str)
    
    # Fast semantic recommendations
    recs = set(static_recs)
    
    person = g.value(user_uri, moreo.has_person_identity)
    if person:
        for n in g.objects(person, moreo.has_nationality):
            recs.update(movie_nationalities[str(n)])
            
    user_preferences = set(g.objects(user_uri, moreo.has_preference))
    for pref in user_preferences:
        pref_str = str(pref)
        if pref_str in person_movies:
            recs.update(person_movies[pref_str])
        if pref_str in award_movies:
            recs.update(award_movies[pref_str])
            
    semantic_rec_uris = list(recs)
    num_interactions = user_ratings_count[user_uri_str]
    
    all_recommendations[user_uri_str] = len(semantic_rec_uris)

print(f"Fast loop completed in {time.time() - start_loop:.4f} seconds.")
print(f"First 5 users recommendations count: {list(all_recommendations.items())[:5]}")
