import os
import sys
import rdflib
import torch
import uuid
import threading
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.semantic.validation import validate_ontology
from src.semantic.recommendation import gerar_recomendacao_usuario, obter_recomendacao_semantica_rapida
from src.inductive.model import MORE_RGCN
from src.inductive.train import run_training

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_populado_1m.owl")
ONTOLOGY_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_ontology.ttl")
SHACL_PATH = os.path.join(PROJECT_ROOT, "ontology", "moreo_shacl.ttl")
SPARQL_PATH = os.path.join(PROJECT_ROOT, "sparql", "subgraph.sparql")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "model.pt")

graph_cache = {}
training_status = {"status": "idle"}
graph_lock = threading.Lock()

def get_full_graph():
    with graph_lock:
        if "graph" not in graph_cache:
            g = rdflib.Graph()
            g.parse(DATA_PATH, format="xml")
            graph_cache["graph"] = g
        return graph_cache["graph"]

class ValidationRequest(BaseModel):
    data_path: str = DATA_PATH
    shacl_path: str = SHACL_PATH

class UserRegistration(BaseModel):
    user_id: str
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    name: str
    age: int = Field(..., gt=0)
    gender: str
    nationality: str
    phone: str = None
    preferred_awards: list[str] = []
    preferred_directors: list[str] = []
    preferred_actors: list[str] = []
    preferred_genres: list[str] = []

class RatingSubmission(BaseModel):
    user_id: str
    movie_id: str
    score: int = Field(..., ge=1, le=5)
    timestamp: str = None

@app.post("/validate")
def validate(request: ValidationRequest):
    try:
        conforms, report = validate_ontology(request.data_path, request.shacl_path)
        return {"conforms": conforms, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train")
def train(background_tasks: BackgroundTasks, num_epochs: int = 50, lr: float = 0.01, batch_size: int = 1024):
    if training_status["status"] == "running":
        return {"message": "Training is already in progress."}

    def do_training():
        training_status["status"] = "running"
        try:
            run_training(DATA_PATH, ONTOLOGY_PATH, num_epochs, lr, batch_size, MODEL_PATH)
            training_status["status"] = "completed"
        except Exception as e:
            training_status["status"] = "failed"
            training_status["error"] = str(e)

    background_tasks.add_task(do_training)
    return {"message": "Training started in background."}

@app.get("/train/status")
def get_train_status():
    return training_status

@app.post("/users")
def register_user(request: UserRegistration):
    g = get_full_graph()
    moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
    rdf = rdflib.RDF
    xsd = rdflib.XSD
    
    user_uri = moreo[f"USER_{request.user_id}"]
    
    with graph_lock:
        if (user_uri, rdf.type, moreo.User) in g:
            raise HTTPException(status_code=400, detail="User already exists.")
        
        g.add((user_uri, rdf.type, moreo.User))
        g.add((user_uri, moreo.has_email, rdflib.Literal(request.email, datatype=xsd.string)))
        if request.phone:
            g.add((user_uri, moreo.has_phone, rdflib.Literal(request.phone, datatype=xsd.string)))
            
        person_uri = moreo[f"PERSON_{request.user_id}"]
        g.add((user_uri, moreo.has_person_identity, person_uri))
        
        g.add((person_uri, rdf.type, moreo.Person))
        g.add((person_uri, moreo.has_name, rdflib.Literal(request.name, datatype=xsd.string)))
        g.add((person_uri, moreo.has_age, rdflib.Literal(request.age, datatype=xsd.positiveInteger)))
        
        nation_uri = moreo[f"NATION_{request.nationality.replace(' ', '_')}"]
        g.add((nation_uri, rdf.type, moreo.Nation))
        g.add((nation_uri, moreo.has_name, rdflib.Literal(request.nationality, datatype=xsd.string)))
        g.add((person_uri, moreo.has_nationality, nation_uri))
        
        quality_uri = moreo[f"QUALITY_{request.user_id}"]
        g.add((quality_uri, rdf.type, moreo.GenderQuality))
        g.add((quality_uri, moreo.direct_quality_of, person_uri))
        g.add((person_uri, moreo.has_quality, quality_uri))
        
        region_uri = moreo[f"REGION_{request.user_id}"]
        g.add((region_uri, rdf.type, moreo.GenderRegion))
        g.add((region_uri, moreo.constant_quale_of, quality_uri))
        g.add((region_uri, moreo.has_gender_label, rdflib.Literal(request.gender, datatype=xsd.string)))
        
        # Link preferences
        for pref_uri_str in request.preferred_awards + request.preferred_directors + request.preferred_actors + request.preferred_genres:
            if pref_uri_str.startswith("http"):
                pref_uri = rdflib.URIRef(pref_uri_str)
            else:
                pref_uri = moreo[pref_uri_str]
            g.add((user_uri, moreo.has_preference, pref_uri))
            
        g.serialize(destination=DATA_PATH, format="xml")
        
    return {"message": "User registered successfully", "user_uri": str(user_uri)}

@app.post("/ratings")
def submit_rating(request: RatingSubmission):
    g = get_full_graph()
    moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
    rdf = rdflib.RDF
    xsd = rdflib.XSD
    
    user_uri = moreo[f"USER_{request.user_id}"]
    
    if request.movie_id.startswith("http"):
        movie_uri = rdflib.URIRef(request.movie_id)
    else:
        movie_uri = moreo[request.movie_id]
        
    with graph_lock:
        if (user_uri, rdf.type, moreo.User) not in g:
            raise HTTPException(status_code=404, detail="User not found.")
        if (movie_uri, rdf.type, moreo.Movie) not in g:
            raise HTTPException(status_code=404, detail="Movie not found.")
            
        rating_id = f"RATING_{request.user_id}_{uuid.uuid4().hex[:8]}"
        rating_uri = moreo[rating_id]
        
        g.add((rating_uri, rdf.type, moreo.UserRating))
        g.add((rating_uri, moreo.is_performed_by, user_uri))
        g.add((rating_uri, moreo.is_about, movie_uri))
        g.add((rating_uri, moreo.has_score, rdflib.Literal(request.score, datatype=xsd.nonNegativeInteger)))
        
        ts = request.timestamp
        if not ts:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        g.add((rating_uri, moreo.has_timestamp, rdflib.Literal(ts, datatype=xsd.dateTimeStamp)))
        
        g.add((user_uri, moreo.performs_rating, rating_uri))
        
        g.serialize(destination=DATA_PATH, format="xml")
        
    return {"message": "Rating submitted successfully", "rating_uri": str(rating_uri)}

@app.get("/awards")
def get_awards():
    g = get_full_graph()
    query = """
    PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
    SELECT DISTINCT ?award WHERE {
      ?award rdf:type :Award .
    } ORDER BY ?award
    """
    res = []
    with graph_lock:
        rows = list(g.query(query))
    for row in rows:
        uri = str(row.award)
        localname = uri.split("#")[-1]
        name = localname.replace("AWARD_", "").replace("_", " ")
        res.append({"uri": uri, "name": name})
    return res

@app.get("/genres")
def get_genres():
    g = get_full_graph()
    query = """
    PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
    SELECT DISTINCT ?genre WHERE {
      ?genre rdf:type :FilmGenre .
    } ORDER BY ?genre
    """
    res = []
    with graph_lock:
        rows = list(g.query(query))
    for row in rows:
        uri = str(row.genre)
        name = uri.split("#")[-1].replace("GENRE_", "")
        res.append({"uri": uri, "name": name})
    return res

@app.get("/directors")
def get_directors():
    g = get_full_graph()
    query = """
    PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
    SELECT DISTINCT ?person ?name WHERE {
      ?role rdf:type :DirectorRole .
      ?person :has_role ?role .
      ?person :has_name ?name .
    } ORDER BY ?name LIMIT 100
    """
    res = []
    with graph_lock:
        rows = list(g.query(query))
    for row in rows:
        res.append({"uri": str(row.person), "name": str(row.name)})
    return res

@app.get("/actors")
def get_actors():
    g = get_full_graph()
    query = """
    PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
    SELECT DISTINCT ?person ?name WHERE {
      ?role rdf:type :ActorRole .
      ?person :has_role ?role .
      ?person :has_name ?name .
    } ORDER BY ?name LIMIT 100
    """
    res = []
    with graph_lock:
        rows = list(g.query(query))
    for row in rows:
        res.append({"uri": str(row.person), "name": str(row.name)})
    return res

@app.get("/recommend")
def recommend(user_id: str, top_n: int = 10):
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=400, detail="Model not trained yet.")
    
    checkpoint = torch.load(MODEL_PATH)
    model = MORE_RGCN(checkpoint["num_nodes"], checkpoint["num_relations"])
    model.load_state_dict(checkpoint["model_state_dict"])

    from src.inductive.graph_builder import OntologyGraphBuilder
    builder = OntologyGraphBuilder("http://www.semanticweb.org/ontologies/2026/3/MOREO#performs_rating")
    builder.node_to_idx = checkpoint["node_to_idx"]
    builder.idx_to_node = checkpoint["idx_to_node"]
    builder.pred_to_idx = checkpoint["pred_to_idx"]

    test_edge_index, test_edge_type = checkpoint["test_graph"]
    user_uri = f"http://www.semanticweb.org/ontologies/2026/3/MOREO#USER_{user_id}"
    user_ref = rdflib.URIRef(user_uri)
    moreo_ns = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
    
    g = get_full_graph()
    
    # Verify user existence in ontology graph
    user_exists = False
    with graph_lock:
        if (user_ref, rdflib.RDF.type, moreo_ns.User) in g:
            user_exists = True

    if not user_exists:
        raise HTTPException(status_code=404, detail="User not found in ontology dataset.")

    candidate_movies = [builder.idx_to_node[idx] for idx in checkpoint["all_movie_indices"]]

    try:
        with graph_lock:
            semantic_rec_uris = gerar_recomendacao_usuario(g, ONTOLOGY_PATH, SPARQL_PATH, user_id)
        semantic_scores = {m: 1.0 for m in semantic_rec_uris}
    except Exception as e:
        print(f"[Recommend] Error generating semantic recommendations: {e}")
        semantic_scores = {}

    if user_uri in builder.node_to_idx:
        from src.inductive.inference import NeuralInferenceEngine
        inference_engine = NeuralInferenceEngine(model, builder)
        neural_scores = inference_engine.get_predictions_for_user(user_uri, candidate_movies, test_edge_index, test_edge_type)
    else:
        # Fallback to semantic-only recommendations for new/unseen users
        print(f"[Recommend] User {user_id} is new/unseen by GNN model. Falling back to semantic-only scores.")
        neural_scores = {m: 0.0 for m in candidate_movies}

    num_interactions = 0
    with graph_lock:
        for s, p, o in g:
            if str(s) == user_uri and str(p) == "http://www.semanticweb.org/ontologies/2026/3/MOREO#performs_rating":
                num_interactions += 1

    from src.ranking_engine.ranking_engine import MORE_RankingEngine
    ranking_engine = MORE_RankingEngine()
    final_ranking = ranking_engine.compute_final_ranking(candidate_movies, semantic_scores, neural_scores, num_interactions, top_n)

    moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
    recommendations_with_metadata = []
    
    for item in final_ranking:
        movie_uri_str = item[0]
        movie_uri = rdflib.URIRef(movie_uri_str)
        
        with graph_lock:
            # Title
            title_lit = g.value(subject=movie_uri, predicate=moreo.has_title)
            title = str(title_lit) if title_lit else movie_uri_str.split("#")[-1]
            
            # Genres
            genres = [str(o).split("#")[-1].replace("GENRE_", "") for s, p, o in g.triples((movie_uri, moreo.has_genre, None))]
            
            # Directors
            directors_query = f"""
            PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
            SELECT DISTINCT ?name WHERE {{
              ?role :is_played_in <{movie_uri_str}> .
              ?role rdf:type :DirectorRole .
              ?person :has_role ?role .
              ?person :has_name ?name .
            }}
            """
            directors = [str(r.name) for r in g.query(directors_query)]
            
            # Actors (limit to top 5 actors to avoid rendering massive lists on flashcards)
            actors_query = f"""
            PREFIX : <http://www.semanticweb.org/ontologies/2026/3/MOREO#>
            SELECT DISTINCT ?name WHERE {{
              ?role :is_played_in <{movie_uri_str}> .
              ?role rdf:type :ActorRole .
              ?person :has_role ?role .
              ?person :has_name ?name .
            }} LIMIT 5
            """
            actors = [str(r.name) for r in g.query(actors_query)]
        
        recommendations_with_metadata.append({
            "movie_uri": movie_uri_str,
            "movie_id": movie_uri_str.split("#")[-1],
            "title": title,
            "genres": genres,
            "directors": directors,
            "actors": actors,
            "score": item[1]
        })

    return {
        "user_id": user_id,
        "num_interactions": num_interactions,
        "alpha": ranking_engine._calculate_alpha(num_interactions),
        "recommendations": recommendations_with_metadata
    }

@app.get("/evaluate")
def evaluate(k: int = 20):
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=400, detail="Model not trained yet.")
    
    checkpoint = torch.load(MODEL_PATH)
    model = MORE_RGCN(checkpoint["num_nodes"], checkpoint["num_relations"])
    model.load_state_dict(checkpoint["model_state_dict"])

    from src.inductive.graph_builder import OntologyGraphBuilder
    builder = OntologyGraphBuilder("http://www.semanticweb.org/ontologies/2026/3/MOREO#performs_rating")
    builder.node_to_idx = checkpoint["node_to_idx"]
    builder.idx_to_node = checkpoint["idx_to_node"]
    builder.pred_to_idx = checkpoint["pred_to_idx"]

    # Load evaluation data from checkpoint
    train_edge_index, train_edge_type = checkpoint["train_graph"]   # ← use train graph (no leakage)
    test_gt = checkpoint["test_ground_truth"]
    candidate_movies = [builder.idx_to_node[idx] for idx in checkpoint["all_movie_indices"]]
    # train_seen: user_uri -> set of movie_uris rated in training (for filtered ranking)
    train_seen = checkpoint.get("train_seen", {})  # backwards-compat if old checkpoint

    from src.inductive.inference import NeuralInferenceEngine
    from src.ranking_engine.ranking_engine import MORE_RankingEngine
    from src.evaluation.evaluator import MORE_Evaluator
    from collections import defaultdict

    inference_engine = NeuralInferenceEngine(model, builder)
    ranking_engine = MORE_RankingEngine()
    evaluator = MORE_Evaluator(k=k)

    g = get_full_graph()
    moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
    rdf = rdflib.RDF

    # Helper to check if a URI represents a Movie
    def is_movie(m):
        for t in g.objects(m, rdf.type):
            t_str = str(t)
            if "Movie" in t_str or "Documentary" in t_str or "FictionMovie" in t_str:
                return True
        return False

    # Pre-compute static recommendations
    static_recs = set()
    # 1. Global Rating > 4.5
    for gr in g.subjects(rdf.type, moreo.GlobalRating):
        score_lit = g.value(gr, moreo.has_average_score)
        try:
            if score_lit and float(score_lit) > 4.5:
                for m in g.objects(gr, moreo.is_global_rating_quality_of):
                    if is_movie(m):
                        static_recs.add(str(m))
        except Exception:
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

    # Pre-compute user ratings count
    user_ratings_count = defaultdict(int)
    for s, p, o in g.triples((None, moreo.performs_rating, None)):
        user_ratings_count[str(s)] += 1

    all_recommendations = {}

    # Pre-compute node embeddings using TRAIN graph only (no leakage)
    model.eval()
    with torch.no_grad():
        node_embeddings = model(train_edge_index, train_edge_type)

    for user_uri in test_gt.keys():
        user_uri_ref = rdflib.URIRef(user_uri)
        
        # Fast semantic recommendations using pre-computed index
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

        # Filtered ranking: exclude movies the user already rated in training
        user_seen = train_seen.get(user_uri, set())
        filtered_candidates = [m for m in candidate_movies if m not in user_seen]

        neural_scores = inference_engine.get_predictions_for_user(
            user_uri, filtered_candidates, node_embeddings=node_embeddings
        )
        
        num_interactions = user_ratings_count[user_uri]

        final_ranking = ranking_engine.compute_final_ranking(
            filtered_candidates, semantic_scores, neural_scores, num_interactions, k
        )
        all_recommendations[user_uri] = [item[0] for item in final_ranking]

    metrics = evaluator.evaluate_system(all_recommendations, test_gt)
    return metrics
