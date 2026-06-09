from rdflib import URIRef, Literal, RDF, RDFS, XSD
from ..queries import get_list_movies_query

class MovieCrudMixin:
    def create_movie(
        self,
        title: str,
        production_date: str,  # YYYY-MM-DD
        release_date: str,     # YYYY-MM-DD
        language: str,
        nationality_uri: str,
        genre_uris: list[str],
        director_person_uri: str,
        actor_person_uris: list[str] = None,
        screenwriter_person_uris: list[str] = None
    ) -> URIRef:
        uri = self.get_uri(title)
        
        # Determine if it is a Documentary or FictionMovie
        # If any of the genre_uris is a DocumentaryGenre in the graph, type is Documentary
        is_doc = False
        for g_uri in genre_uris:
            g_ref = URIRef(g_uri)
            if (g_ref, RDF.type, self.MOREO.DocumentaryGenre) in self.graph:
                is_doc = True
                break
                
        movie_type = self.MOREO.Documentary if is_doc else self.MOREO.FIctionMovie
        
        # Add Movie type and specific class
        self.graph.add((uri, RDF.type, self.MOREO.Movie))
        self.graph.add((uri, RDF.type, movie_type))
        if not is_doc:
            # Also add FictionMovie (lowercase i) to satisfy the SHACL shape
            self.graph.add((uri, RDF.type, URIRef(str(self.MOREO) + "FictionMovie")))
        
        # Properties
        self.graph.add((uri, RDFS.label, Literal(title)))
        self.graph.add((uri, self.MOREO.has_title, Literal(title)))
        self.graph.add((uri, self.MOREO.has_language, Literal(language)))
        
        # Dates (Formatted as ISO dateTime)
        self.graph.add((uri, self.MOREO.has_production_date, Literal(f"{production_date}T00:00:00", datatype=XSD.dateTime)))
        self.graph.add((uri, self.MOREO.has_release_date, Literal(f"{release_date}T00:00:00", datatype=XSD.dateTime)))
        
        # Nationality and its inverse
        self.graph.add((uri, self.MOREO.has_nationality, URIRef(nationality_uri)))
        self.graph.add((URIRef(nationality_uri), self.MOREO.is_nationality_of, uri))
        
        # Genres and their inverses
        for g_uri in genre_uris:
            g_ref = URIRef(g_uri)
            self.graph.add((uri, self.MOREO.has_genre, g_ref))
            self.graph.add((g_ref, self.MOREO.is_genre_of, uri))
            
        # Helper to create and link roles
        def add_role(person_uri_str, role_class, role_suffix):
            p_uri = URIRef(person_uri_str)
            p_name = p_uri.split('#')[-1]
            clean_t = self.clean_name(title)
            role_uri = self.get_uri(f"{role_suffix}_{clean_t}_{p_name}")
            
            self.graph.add((role_uri, RDF.type, self.MOREO.Role))
            self.graph.add((role_uri, RDF.type, role_class))
            
            # Relations
            self.graph.add((uri, self.MOREO.contains_role, role_uri))
            self.graph.add((role_uri, self.MOREO.is_role_of, p_uri))
            self.graph.add((role_uri, self.MOREO.is_played_in, uri))
            
        # Director Role
        add_role(director_person_uri, self.MOREO.DirectorRole, "DirectorRole")
        
        # Actor Roles
        if actor_person_uris:
            for act_uri in actor_person_uris:
                add_role(act_uri, self.MOREO.ActorRole, "ActorRole")
                
        # Screenwriter Roles
        if screenwriter_person_uris:
            for scr_uri in screenwriter_person_uris:
                add_role(scr_uri, self.MOREO.ScreenwriterRole, "ScreenwriterRole")
                
        # Initialize GlobalRating for the Movie
        clean_title = self.clean_name(title)
        gr_uri = self.get_uri(f"GlobalRating_{clean_title}")
        self.graph.add((gr_uri, RDF.type, self.MOREO.GlobalRating))
        self.graph.add((gr_uri, self.MOREO.has_global_rating_quality, uri))
        self.graph.add((gr_uri, self.MOREO.has_average_score, Literal(0.0, datatype=XSD.float)))
        
        self.save()
        return uri

    def list_movies(self, genre: str = None, actor: str = None, nationality: str = None, director: str = None) -> list[dict]:
        query = get_list_movies_query(genre=genre, actor=actor, director=director, nationality=nationality)
        res = self.execute_query(query)
        results = []
        for row in res:
            results.append({
                "uri": str(row[0]),
                "title": str(row[1]) if row[1] else "",
                "production_date": str(row[2]).split('T')[0] if row[2] else "",
                "release_date": str(row[3]).split('T')[0] if row[3] else "",
                "language": str(row[4]) if row[4] else "",
                "nationality_uri": str(row[5]) if row[5] else "",
                "nationality": str(row[6]) if row[6] else ""
            })
        return results

    def get_movie(self, movie_uri: str) -> dict:
        movie_ref = URIRef(movie_uri)
        if (movie_ref, RDF.type, self.MOREO.Movie) not in self.graph:
            return {}
            
        title = str(self.graph.value(movie_ref, self.MOREO.has_title) or "")
        lang = str(self.graph.value(movie_ref, self.MOREO.has_language) or "")
        
        prod_date = self.graph.value(movie_ref, self.MOREO.has_production_date)
        prod_date_str = str(prod_date).split('T')[0] if prod_date else ""
        
        rel_date = self.graph.value(movie_ref, self.MOREO.has_release_date)
        rel_date_str = str(rel_date).split('T')[0] if rel_date else ""
        
        nat_uri = str(self.graph.value(movie_ref, self.MOREO.has_nationality) or "")
        nat_name = str(self.graph.value(URIRef(nat_uri), RDFS.label) or "") if nat_uri else ""
        
        genres = [str(g) for g in self.graph.objects(movie_ref, self.MOREO.has_genre)]
        
        # Roles and Persons
        directors = []
        actors = []
        screenwriters = []
        
        for role in self.graph.objects(movie_ref, self.MOREO.contains_role):
            person_uri = self.graph.value(role, self.MOREO.is_role_of)
            if not person_uri:
                continue
            person_name = str(self.graph.value(person_uri, RDFS.label) or person_uri.split('#')[-1])
            person_info = {"uri": str(person_uri), "name": person_name}
            
            if (role, RDF.type, self.MOREO.DirectorRole) in self.graph:
                directors.append(person_info)
            elif (role, RDF.type, self.MOREO.ActorRole) in self.graph:
                actors.append(person_info)
            elif (role, RDF.type, self.MOREO.ScreenwriterRole) in self.graph:
                screenwriters.append(person_info)
                
        # Global rating
        gr_uri = self.graph.value(predicate=self.MOREO.has_global_rating_quality, object=movie_ref)
        avg_score = 0.0
        if gr_uri:
            avg_score = float(self.graph.value(gr_uri, self.MOREO.has_average_score) or 0.0)
            
        return {
            "uri": movie_uri,
            "title": title,
            "production_date": prod_date_str,
            "release_date": rel_date_str,
            "language": lang,
            "nationality_uri": nat_uri,
            "nationality": nat_name,
            "genres": genres,
            "directors": directors,
            "actors": actors,
            "screenwriters": screenwriters,
            "global_rating": avg_score
        }
