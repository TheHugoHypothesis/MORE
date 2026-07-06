import os
import time
import torch
import rdflib
from collections import defaultdict
import random
import sys

PROJECT_ROOT = "/home/elliot/Área de trabalho/Trabalho ontologias/Entrega 2/MORE/system"
sys.path.append(PROJECT_ROOT)
DATA_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_populado_1m.owl")
ONTOLOGY_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_ontology.ttl")

from src.inductive.graph_builder import OntologyGraphBuilder
from src.inductive.model import MORE_RGCN
from src.inductive.loss import BPREngine
from src.inductive.inference import NeuralInferenceEngine
from src.ranking_engine.ranking_engine import MORE_RankingEngine
from src.evaluation.evaluator import MORE_Evaluator

print("Loading graph...")
g = rdflib.Graph()
g.parse(DATA_PATH, format="xml")
print("Mapping ontology...")
builder = OntologyGraphBuilder("http://www.semanticweb.org/ontologies/2026/3/MOREO#performs_rating")
builder.fit_mappings(g)

print("Splitting...")
train_data, val_data, test_data, train_pairs, val_gt, test_gt = builder.build_split_datasets(g)
train_edge_index, train_edge_type = train_data
test_edge_index, test_edge_type = test_data
all_movie_indices = builder.get_movie_indices(g)

model = MORE_RGCN(num_nodes=builder.num_nodes, num_relations=builder.num_relations)
bpr_engine = BPREngine(model, train_pairs, all_movie_indices)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

num_epochs = 15
batch_size = 1024

print(f"Num train pairs: {len(train_pairs)}")
steps_per_epoch = max(1, len(train_pairs) // batch_size)
print(f"Steps per epoch: {steps_per_epoch}")

model.train()
for epoch in range(num_epochs):
    epoch_loss = 0.0
    for step in range(steps_per_epoch):
        optimizer.zero_grad()
        node_embeddings = model(train_edge_index, train_edge_type)
        u, pos, neg = bpr_engine.sample_triplets(batch_size=batch_size)
        if len(u) == 0:
            break
        loss = bpr_engine.compute_bpr_loss(node_embeddings, u, pos, neg)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    print(f"Epoch {epoch+1}/{num_epochs} | Loss: {epoch_loss / steps_per_epoch:.4f}")

# Now evaluate
model.eval()
inference_engine = NeuralInferenceEngine(model, builder)
ranking_engine = MORE_RankingEngine()
evaluator = MORE_Evaluator(k=10)

moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
rdf = rdflib.RDF

# Indexing static
static_recs = set()
for gr in g.subjects(rdf.type, moreo.GlobalRating):
    score_lit = g.value(gr, moreo.has_average_score)
    try:
        if score_lit and float(score_lit) > 4.5:
            for m in g.objects(gr, moreo.is_global_rating_quality_of):
                static_recs.add(str(m))
    except Exception:
        pass

for role_type in [moreo.Role, moreo.DirectorRole, moreo.ActorRole]:
    for role in g.subjects(rdf.type, role_type):
        m = g.value(role, moreo.is_played_in)
        if m:
            for award in g.subjects(moreo.is_award_of, role):
                date_lit = g.value(award, moreo.has_award_date)
                if date_lit and "2026" in str(date_lit):
                    static_recs.add(str(m))
                    break

movie_nationalities = defaultdict(set)
for movie_type in [moreo.Movie, moreo.FictionMovie, moreo.Documentary]:
    for m in g.subjects(rdf.type, movie_type):
        for n in g.objects(m, moreo.has_nationality):
            movie_nationalities[str(n)].add(str(m))

person_movies = defaultdict(set)
for role_type in [moreo.Role, moreo.DirectorRole, moreo.ActorRole]:
    for role in g.subjects(rdf.type, role_type):
        m = g.value(role, moreo.is_played_in)
        if m:
            for person in g.subjects(moreo.has_role, role):
                person_movies[str(person)].add(str(m))

award_movies = defaultdict(set)
for award in g.subjects(rdf.type, moreo.Award):
    for m in g.objects(award, moreo.is_award_of):
        award_movies[str(award)].add(str(m))

user_ratings_count = defaultdict(int)
for s, p, o in g.triples((None, moreo.performs_rating, None)):
    user_ratings_count[str(s)] += 1

candidate_movies = [builder.idx_to_node[idx] for idx in all_movie_indices]
all_recommendations = {}

with torch.no_grad():
    node_embeddings = model(test_edge_index, test_edge_type)

for user_uri in test_gt.keys():
    user_uri_ref = rdflib.URIRef(user_uri)
    recs = set(static_recs)
    person = g.value(user_uri_ref, moreo.has_person_identity)
    if person:
        for n in g.objects(person, moreo.has_nationality):
            recs.update(movie_nationalities[str(n)])
            
    user_preferences = set(g.objects(user_uri_ref, moreo.has_preference))
    for pref in user_preferences:
        pref_str = str(pref)
        if pref_str in person_movies:
            recs.update(person_movies[pref_str])
        if pref_str in award_movies:
            recs.update(award_movies[pref_str])
            
    semantic_scores = {m: 1.0 for m in recs}
    neural_scores = inference_engine.get_predictions_for_user(user_uri, candidate_movies, node_embeddings=node_embeddings)
    num_interactions = user_ratings_count[user_uri]

    final_ranking = ranking_engine.compute_final_ranking(candidate_movies, semantic_scores, neural_scores, num_interactions, 10)
    all_recommendations[user_uri] = [item[0] for item in final_ranking]

metrics = evaluator.evaluate_system(all_recommendations, test_gt)
print("Evaluation results:", metrics)
