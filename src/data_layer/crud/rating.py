import datetime
import hashlib
from rdflib import URIRef, Literal, RDF, XSD
from ..queries import GET_USER_RATINGS, GET_MOVIE_RATINGS

class RatingCrudMixin:
    def create_rating(self, user_uri: str, movie_uri: str, score: int) -> URIRef:
        user_ref = URIRef(user_uri)
        movie_ref = URIRef(movie_uri)
        
        # Validate score range
        if not (1 <= score <= 5):
            raise ValueError("Nota deve ser entre 1 e 5.")
            
        # Timezone-aware timestamp in UTC
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Create unique URI for rating
        user_name = user_ref.split('#')[-1]
        movie_name = movie_ref.split('#')[-1]
        hash_val = hashlib.md5(f"{user_name}_{movie_name}_{timestamp}".encode()).hexdigest()[:8]
        rating_uri = self.get_uri(f"UserRating_{user_name}_{movie_name}_{hash_val}")
        
        # Add to graph
        self.graph.add((rating_uri, RDF.type, self.MOREO.UserRating))
        self.graph.add((rating_uri, self.MOREO.has_score, Literal(score, datatype=XSD.nonNegativeInteger)))
        self.graph.add((rating_uri, self.MOREO.is_about, movie_ref))
        self.graph.add((rating_uri, self.MOREO.has_timestamp, Literal(timestamp, datatype=XSD.dateTimeStamp)))
        self.graph.add((user_ref, self.MOREO.performs_rating, rating_uri))
        
        self.save()
        
        # Update GlobalRating average for the movie
        self.update_global_rating(movie_uri)
        
        return rating_uri

    def get_user_ratings(self, user_uri: str) -> list[dict]:
        user_ref = URIRef(user_uri)
        res = self.graph.query(GET_USER_RATINGS, initNs={"moreo": self.MOREO}, initBindings={"user_uri": user_ref})
        results = []
        for row in res:
            results.append({
                "rating_uri": str(row[0]),
                "movie_uri": str(row[1]),
                "movie_title": str(row[2]) if row[2] else "",
                "score": int(row[3]),
                "timestamp": str(row[4]) if row[4] else ""
            })
        return results

    def update_global_rating(self, movie_uri: str) -> float:
        movie_ref = URIRef(movie_uri)
        res = self.graph.query(GET_MOVIE_RATINGS, initNs={"moreo": self.MOREO}, initBindings={"movie_ref": movie_ref})
        scores = [int(row[0]) for row in res]
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Get or create GlobalRating Quality node
        gr_uri = self.graph.value(predicate=self.MOREO.has_global_rating_quality, object=movie_ref)
        if not gr_uri:
            clean_title = movie_ref.split('#')[-1]
            gr_uri = self.get_uri(f"GlobalRating_{clean_title}")
            self.graph.add((gr_uri, RDF.type, self.MOREO.GlobalRating))
            self.graph.add((gr_uri, self.MOREO.has_global_rating_quality, movie_ref))
            
        # Update/Set average score
        self.graph.set((gr_uri, self.MOREO.has_average_score, Literal(avg_score, datatype=XSD.float)))
        self.save()
        return avg_score
