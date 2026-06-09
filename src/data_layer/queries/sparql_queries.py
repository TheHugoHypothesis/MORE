LIST_NATIONS = """
SELECT DISTINCT ?uri ?name WHERE {
    ?uri a moreo:Nation .
    OPTIONAL { ?uri rdfs:label ?name }
} ORDER BY ?name
"""

LIST_GENRES = """
SELECT DISTINCT ?uri ?name ?type WHERE {
    ?uri a moreo:FilmGenre .
    OPTIONAL { ?uri moreo:has_name ?name }
    OPTIONAL {
        ?uri a ?type .
        FILTER (?type != moreo:FilmGenre && ?type != owl:Class)
    }
} ORDER BY ?name
"""

LIST_PERSONS = """
SELECT DISTINCT ?uri ?name ?age ?nationality_uri ?nationality_name ?gender WHERE {
    ?uri a moreo:Person .
    OPTIONAL { ?uri moreo:has_name ?name }
    OPTIONAL { ?uri moreo:has_age ?age }
    OPTIONAL {
        ?uri moreo:has_nationality ?nationality_uri .
        OPTIONAL { ?nationality_uri rdfs:label ?nationality_name }
    }
    OPTIONAL {
        ?g_qual a moreo:GenderQuality ; dolce:directQualityOf ?uri .
        ?g_reg a moreo:GenderRegion ; dolce:constantQualeOf ?g_qual ; moreo:has_gender_label ?gender .
    }
} ORDER BY ?name
"""

LIST_USERS = """
SELECT DISTINCT ?uri ?email ?phone WHERE {
    ?uri a moreo:User .
    OPTIONAL { ?uri moreo:has_email ?email }
    OPTIONAL { ?uri moreo:has_phone ?phone }
} ORDER BY ?email
"""

GET_USER_RATINGS = """
SELECT DISTINCT ?rating ?movie_uri ?movie_title ?score ?timestamp WHERE {
    ?user_uri moreo:performs_rating ?rating .
    ?rating a moreo:UserRating ;
            moreo:is_about ?movie_uri ;
            moreo:has_score ?score .
    OPTIONAL { ?rating moreo:has_timestamp ?timestamp }
    OPTIONAL { ?movie_uri moreo:has_title ?movie_title }
} ORDER BY DESC(?timestamp)
"""

GET_MOVIE_RATINGS = """
SELECT ?score WHERE {
    ?rating a moreo:UserRating ;
            moreo:is_about ?movie_ref ;
            moreo:has_score ?score .
}
"""

LIST_AWARDS = """
SELECT DISTINCT ?uri ?category ?ceremony ?date ?movie ?role ?is_winner WHERE {
    ?uri a moreo:Award ;
         moreo:has_category_name ?category ;
         moreo:has_ceremony_name ?ceremony ;
         moreo:has_award_date ?date .
    OPTIONAL {
        ?uri moreo:is_award_of ?movie .
        ?movie a moreo:Movie .
        BIND(true AS ?is_winner)
    }
    OPTIONAL {
        ?uri moreo:is_award_of ?role .
        ?role a moreo:Role .
        BIND(true AS ?is_winner)
    }
    OPTIONAL {
        ?uri moreo:is_indication_of ?movie .
        ?movie a moreo:Movie .
        BIND(false AS ?is_winner)
    }
    OPTIONAL {
        ?uri moreo:is_indication_of ?role .
        ?role a moreo:Role .
        BIND(false AS ?is_winner)
    }
}
"""

GET_RATING_MATRIX = """
SELECT DISTINCT ?email ?movie_title ?score WHERE {
    ?user_uri moreo:performs_rating ?rating ;
              moreo:has_email ?email .
    ?rating a moreo:UserRating ;
            moreo:is_about ?movie_uri ;
            moreo:has_score ?score .
    ?movie_uri moreo:has_title ?movie_title .
}
"""

EXPORT_TRIPLES_FOR_PYKEEN = """
SELECT DISTINCT ?s ?p ?o WHERE {
    ?s ?p ?o .
    FILTER (isURI(?s) && isURI(?p) && isURI(?o))
    FILTER (
        STRSTARTS(STR(?p), "http://www.semanticweb.org/ontologies/2026/3/MOREO#") ||
        STRSTARTS(STR(?p), "https://w3id.org/DOLCE/OWL/DOLCEbasic#")
    )
    FILTER (?p != rdf:type)
}
"""

def get_list_movies_query(genre: str = None, actor: str = None, director: str = None, nationality: str = None) -> str:
    where_clauses = ["?uri a moreo:Movie ."]
    
    if genre:
        # Escape single quotes in user input for SPARQL safety
        safe_genre = genre.replace("'", "\\'")
        where_clauses.append(f"?uri moreo:has_genre ?g . ?g rdfs:label '{safe_genre}' .")
    if actor:
        safe_actor = actor.replace("'", "\\'")
        where_clauses.append(f"?uri moreo:contains_role ?r_act . ?r_act a moreo:ActorRole ; moreo:is_role_of ?p_act . ?p_act rdfs:label '{safe_actor}' .")
    if director:
        safe_director = director.replace("'", "\\'")
        where_clauses.append(f"?uri moreo:contains_role ?r_dir . ?r_dir a moreo:DirectorRole ; moreo:is_role_of ?p_dir . ?p_dir rdfs:label '{safe_director}' .")
    if nationality:
        safe_nat = nationality.replace("'", "\\'")
        where_clauses.append(f"?uri moreo:has_nationality ?nat_f . ?nat_f rdfs:label '{safe_nat}' .")
        
    where_str = "\n    ".join(where_clauses)
    
    return f"""
SELECT DISTINCT ?uri ?title ?prod_date ?rel_date ?lang ?nat_uri ?nat_name WHERE {{
    {where_str}
    OPTIONAL {{ ?uri moreo:has_title ?title }}
    OPTIONAL {{ ?uri moreo:has_production_date ?prod_date }}
    OPTIONAL {{ ?uri moreo:has_release_date ?rel_date }}
    OPTIONAL {{ ?uri moreo:has_language ?lang }}
    OPTIONAL {{
        ?uri moreo:has_nationality ?nat_uri .
        OPTIONAL {{ ?nat_uri rdfs:label ?nat_name }}
    }}
}} ORDER BY ?title
"""
