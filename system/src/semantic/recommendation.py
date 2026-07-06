import os
import rdflib
import time
from owlready2 import *

def gerar_recomendacao_usuario(grafo_completo_rdflib, caminho_ontologia_base, sparql_query_path, user_id):
    user_uri_str = f"http://www.semanticweb.org/ontologies/2026/3/MOREO#USER_{user_id}"
    user_uri = rdflib.URIRef(user_uri_str)
    
    print(f"[Semantic] Extracting programmatic ABox subgraph for user {user_id}...")
    start_subgraph = time.time()
    
    moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
    rdf = rdflib.RDF
    xsd = rdflib.XSD
    
    subgraph = rdflib.Graph()
    
    # 1. User triples
    for s, p, o in grafo_completo_rdflib.triples((user_uri, None, None)):
        subgraph.add((s, p, o))
        if p == moreo.has_person_identity:
            person_uri = o
            for s2, p2, o2 in grafo_completo_rdflib.triples((person_uri, None, None)):
                subgraph.add((s2, p2, o2))
                if p2 == moreo.has_quality:
                    quality_uri = o2
                    for s3, p3, o3 in grafo_completo_rdflib.triples((quality_uri, None, None)):
                        subgraph.add((s3, p3, o3))
                    for s3, p3, o3 in grafo_completo_rdflib.triples((None, moreo.constant_quale_of, quality_uri)):
                        subgraph.add((s3, p3, o3))
                        for s4, p4, o4 in grafo_completo_rdflib.triples((s3, None, None)):
                            subgraph.add((s4, p4, o4))
                            
    # 2. User ratings
    rated_movies = set()
    for s, p, o in grafo_completo_rdflib.triples((user_uri, moreo.performs_rating, None)):
        subgraph.add((s, p, o))
        rating_uri = o
        for s2, p2, o2 in grafo_completo_rdflib.triples((rating_uri, None, None)):
            subgraph.add((s2, p2, o2))
            if p2 == moreo.is_about:
                rated_movies.add(o2)
                
    # Get user preferences
    user_preferences = set(grafo_completo_rdflib.objects(user_uri, moreo.has_preference))
    
    # 3. Find candidate movies
    all_movies = list(grafo_completo_rdflib.subjects(rdf.type, moreo.Movie))
    candidate_movies = set()
    
    # Add rated movies
    candidate_movies.update(rated_movies)
    
    # Check movie conditions
    for movie in all_movies:
        # Condition 1: Genre preference
        movie_genres = set(grafo_completo_rdflib.objects(movie, moreo.has_genre))
        if movie_genres.intersection(user_preferences):
            candidate_movies.add(movie)
            continue
            
        # Condition 2: Award preference
        movie_awards = set(grafo_completo_rdflib.subjects(moreo.is_award_of, movie)).union(
            grafo_completo_rdflib.subjects(moreo.is_indication_of, movie)
        )
        if movie_awards.intersection(user_preferences):
            candidate_movies.add(movie)
            continue
            
        # Condition 3: Actor/director preference
        movie_roles = list(grafo_completo_rdflib.subjects(moreo.is_played_in, movie))
        has_preferred_person = False
        for role in movie_roles:
            person = grafo_completo_rdflib.value(predicate=moreo.has_role, object=role)
            if person in user_preferences:
                has_preferred_person = True
                break
                
            role_awards = set(grafo_completo_rdflib.subjects(moreo.is_award_of, role))
            if role_awards.intersection(user_preferences):
                has_preferred_person = True
                break
                
        if has_preferred_person:
            candidate_movies.add(movie)
            continue
            
        # Condition 4: Global rating > 4.5
        for gr in grafo_completo_rdflib.subjects(moreo.is_global_rating_quality_of, movie):
            score_lit = grafo_completo_rdflib.value(gr, moreo.has_average_score)
            try:
                if score_lit and float(score_lit) > 4.5:
                    candidate_movies.add(movie)
                    break
            except (ValueError, TypeError):
                pass
        if movie in candidate_movies:
            continue
            
        # Condition 5: 2026 award
        has_2026_award = False
        for role in movie_roles:
            for a in grafo_completo_rdflib.subjects(moreo.is_award_of, role):
                date_lit = grafo_completo_rdflib.value(a, moreo.has_award_date)
                if date_lit:
                    date_str = str(date_lit)
                    if "2026" in date_str:
                        has_2026_award = True
                        break
            if has_2026_award:
                break
        if has_2026_award:
            candidate_movies.add(movie)
            continue
            
    # Fallback to avoid empty candidate movies for new users or small graphs
    if len(candidate_movies) == 0 and len(all_movies) > 0:
        print("[Semantic] No candidate movies matched preferences. Fallback to first 50 movies.")
        candidate_movies.update(all_movies[:50])
        
    # 4. Populate subgraph with candidate movie triples and their related entities
    for movie in candidate_movies:
        for s, p, o in grafo_completo_rdflib.triples((movie, None, None)):
            # Skip title and date to reduce subgraph size and speed up Pellet
            if p in [moreo.has_title, moreo.has_production_date, moreo.has_release_date, moreo.has_language]:
                continue
            subgraph.add((s, p, o))
            
        # Roles played in movie
        for s, p, o in grafo_completo_rdflib.triples((None, moreo.is_played_in, movie)):
            subgraph.add((s, p, o))
            role = s
            for s2, p2, o2 in grafo_completo_rdflib.triples((role, None, None)):
                subgraph.add((s2, p2, o2))
            
            # Restrict person triples to avoid transitive graph explosion
            for person in grafo_completo_rdflib.subjects(moreo.has_role, role):
                subgraph.add((person, rdf.type, moreo.Person))
                subgraph.add((person, moreo.has_role, role))
                
        # Awards and indications of movie
        for p_prop in [moreo.is_award_of, moreo.is_indication_of]:
            for award in grafo_completo_rdflib.subjects(p_prop, movie):
                subgraph.add((award, p_prop, movie))
                for s2, p2, o2 in grafo_completo_rdflib.triples((award, None, None)):
                    subgraph.add((s2, p2, o2))
                    
        # Awards of roles played in movie
        for role in grafo_completo_rdflib.subjects(moreo.is_played_in, movie):
            for award in grafo_completo_rdflib.subjects(moreo.is_award_of, role):
                subgraph.add((award, moreo.is_award_of, role))
                for s2, p2, o2 in grafo_completo_rdflib.triples((award, None, None)):
                    subgraph.add((s2, p2, o2))
                    
        # Genres of movie
        for o in grafo_completo_rdflib.objects(movie, moreo.has_genre):
            subgraph.add((movie, moreo.has_genre, o))
            for s2, p2, o2 in grafo_completo_rdflib.triples((o, None, None)):
                subgraph.add((s2, p2, o2))
                
        # Nationalities of movie
        for o in grafo_completo_rdflib.objects(movie, moreo.has_nationality):
            subgraph.add((movie, moreo.has_nationality, o))
            for s2, p2, o2 in grafo_completo_rdflib.triples((o, None, None)):
                subgraph.add((s2, p2, o2))
                
        # Global ratings of movie
        for gr in grafo_completo_rdflib.subjects(moreo.is_global_rating_quality_of, movie):
            subgraph.add((gr, moreo.is_global_rating_quality_of, movie))
            for s2, p2, o2 in grafo_completo_rdflib.triples((gr, None, None)):
                subgraph.add((s2, p2, o2))
                
    print(f"[Semantic] Subgraph built in {time.time() - start_subgraph:.4f} seconds. Size: {len(subgraph)} triples.")
    
    print(f"[Semantic] Merging subgraph with TBox ontology schema from {caminho_ontologia_base}...")
    grafo_mesclado = rdflib.Graph()
    grafo_mesclado.parse(caminho_ontologia_base, format="ttl")
    
    for tripla in subgraph:
        grafo_mesclado.add(tripla)
        
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    temp_dir = os.path.join(project_root, "users_subgraph")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f"temp_inferencia_user_{user_id}.owl")
    grafo_mesclado.serialize(destination=temp_file, format="xml")
    
    print(f"[Semantic] Starting Pellet reasoning on merged TBox/ABox ontology...")
    my_world = World()
    onto = my_world.get_ontology(f"file://{temp_file}").load()
    
    with onto:
        sync_reasoner_pellet(my_world, infer_property_values=True)
        
    print(f"[Semantic] Pellet reasoning completed. Querying recommendations...")
    recomendacoes = []
    usuario_instancia = my_world.search_one(iri=f"*{user_uri_str}")
    if usuario_instancia:
        if hasattr(usuario_instancia, "receives_recommendation_of"):
            for filme in usuario_instancia.receives_recommendation_of:
                recomendacoes.append(str(filme.iri))
                
    try:
        my_world.close()
    except Exception:
        pass
        
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    print(f"[Semantic] Finished. Found {len(recomendacoes)} recommendations for user {user_id}.")
    return recomendacoes

def obter_recomendacao_semantica_rapida(g, user_uri_str):
    moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
    rdf = rdflib.RDF
    user_uri = rdflib.URIRef(user_uri_str)
    
    recs = set()
    
    # Helper to check if a URI represents a Movie
    def is_movie(m):
        for t in g.objects(m, rdf.type):
            t_str = str(t)
            if "Movie" in t_str or "Documentary" in t_str or "FictionMovie" in t_str:
                return True
        return False
        
    # 1. Recomendação global: average score > 4.5
    # Find all global ratings with score > 4.5
    for gr in g.subjects(rdf.type, moreo.GlobalRating):
        score_lit = g.value(gr, moreo.has_average_score)
        try:
            if score_lit and float(score_lit) > 4.5:
                # Find movies associated with this global rating
                for m in g.objects(gr, moreo.is_global_rating_quality_of):
                    if is_movie(m):
                        recs.add(str(m))
        except (ValueError, TypeError):
            pass
            
    # 2. Regra da mesma nacionalidade: user nationality == movie nationality
    person = g.value(user_uri, moreo.has_person_identity)
    if person:
        user_nationalities = set(g.objects(person, moreo.has_nationality))
        if user_nationalities:
            for m in g.subjects(rdf.type, moreo.Movie):
                movie_nationalities = set(g.objects(m, moreo.has_nationality))
                if movie_nationalities.intersection(user_nationalities):
                    recs.add(str(m))
            # also check subclass movie types if any
            for m in g.subjects(rdf.type, moreo.FictionMovie):
                movie_nationalities = set(g.objects(m, moreo.has_nationality))
                if movie_nationalities.intersection(user_nationalities):
                    recs.add(str(m))
            for m in g.subjects(rdf.type, moreo.Documentary):
                movie_nationalities = set(g.objects(m, moreo.has_nationality))
                if movie_nationalities.intersection(user_nationalities):
                    recs.add(str(m))

    # 3. Recomendação por ator e diretor preferido
    user_preferences = set(g.objects(user_uri, moreo.has_preference))
    for pref in user_preferences:
        # Check if pref is a Person
        # To be safe, check if it has a Person type or is used in has_role
        is_person = (pref, rdf.type, moreo.Person) in g or list(g.objects(pref, moreo.has_role))
        if is_person:
            # Find roles of this person: (pref, has_role, role)
            for role in g.objects(pref, moreo.has_role):
                # Find movie: (role, is_played_in, movie)
                for m in g.objects(role, moreo.is_played_in):
                    if is_movie(m):
                        recs.add(str(m))
                        
    # 4. Recomendação de filme anual (2026)
    # Find movies with a role that won an award in 2026
    for role in g.subjects(rdf.type, moreo.Role):
        # Find movie: (role, is_played_in, movie)
        m = g.value(role, moreo.is_played_in)
        if m and is_movie(m):
            # Check awards of this role: (award, is_award_of, role)
            for award in g.subjects(moreo.is_award_of, role):
                date_lit = g.value(award, moreo.has_award_date)
                if date_lit and "2026" in str(date_lit):
                    recs.add(str(m))
                    break
                    
    # Also check director/other role subclasses just in case they are not explicitly typed as Role in ABox
    for role_type in [moreo.DirectorRole, moreo.ActorRole, moreo.WriterRole, moreo.ProducerRole]:
        for role in g.subjects(rdf.type, role_type):
            m = g.value(role, moreo.is_played_in)
            if m and is_movie(m):
                for award in g.subjects(moreo.is_award_of, role):
                    date_lit = g.value(award, moreo.has_award_date)
                    if date_lit and "2026" in str(date_lit):
                        recs.add(str(m))
                        break

    # 5. Preferência de Cerimônia de Filme
    for pref in user_preferences:
        # Check if pref is an Award
        is_award = (pref, rdf.type, moreo.Award) in g or list(g.subjects(moreo.is_award_of, pref))
        if is_award:
            # Find movie: (pref, is_award_of, movie)
            for m in g.objects(pref, moreo.is_award_of):
                if is_movie(m):
                    recs.add(str(m))
                    
    return list(recs)

