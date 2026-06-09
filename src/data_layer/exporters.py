import pandas as pd

class ExporterMixin:
    def get_rating_matrix(self) -> pd.DataFrame:
        query = """
        SELECT DISTINCT ?email ?movie_title ?score WHERE {
            ?user_uri moreo:performs_rating ?rating ;
                      moreo:has_email ?email .
            ?rating a moreo:UserRating ;
                    moreo:is_about ?movie_uri ;
                    moreo:has_score ?score .
            ?movie_uri moreo:has_title ?movie_title .
        }
        """
        res = self.graph.query(query, initNs={"moreo": self.MOREO})
        data = []
        for row in res:
            data.append({
                "user": str(row[0]),
                "movie": str(row[1]),
                "score": float(row[2])
            })
        if not data:
            return pd.DataFrame(columns=["user", "movie", "score"])
        df = pd.DataFrame(data)
        return df.pivot_table(index="user", columns="movie", values="score")

    def export_triples_for_pykeen(self) -> pd.DataFrame:
        # Query relation triples where subject, predicate, and object are URIs.
        # Restrict predicates to MOREO and DOLCE namespaces, filtering out OWL meta-properties.
        query = """
        SELECT DISTINCT ?s ?p ?o WHERE {
            ?s ?p ?o .
            FILTER (isURI(?s) && isURI(?p) && isURI(?o))
            FILTER (
                STRSTARTS(STR(?p), "http://www.semanticweb.org/ontologies/2026/3/MOREO#") ||
                STRSTARTS(STR(?p), "https://w3id.org/DOLCE/OWL/DOLCEbasic#")
            )
            # Filter out standard OWL/RDF schema declarations
            FILTER (?p != rdf:type)
        }
        """
        res = self.graph.query(query)
        data = []
        for row in res:
            data.append({
                "head": str(row[0]),
                "relation": str(row[1]),
                "tail": str(row[2])
            })
        return pd.DataFrame(data, columns=["head", "relation", "tail"])
