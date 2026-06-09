import pandas as pd
from .queries import GET_RATING_MATRIX, EXPORT_TRIPLES_FOR_PYKEEN

class ExporterMixin:
    def get_rating_matrix(self) -> pd.DataFrame:
        res = self.graph.query(GET_RATING_MATRIX, initNs={"moreo": self.MOREO})
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
        res = self.graph.query(EXPORT_TRIPLES_FOR_PYKEEN)
        data = []
        for row in res:
            data.append({
                "head": str(row[0]),
                "relation": str(row[1]),
                "tail": str(row[2])
            })
        return pd.DataFrame(data, columns=["head", "relation", "tail"])
