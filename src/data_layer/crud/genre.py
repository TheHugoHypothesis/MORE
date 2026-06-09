from rdflib import URIRef, Literal, RDF, RDFS
from ..queries import LIST_GENRES

class GenreCrudMixin:
    def create_genre(self, name: str, is_documentary: bool = False) -> URIRef:
        uri = self.get_uri(name)
        genre_type = self.MOREO.DocumentaryGenre if is_documentary else self.MOREO.FictionGenre
        if (uri, RDF.type, genre_type) in self.graph:
            return uri
        self.graph.add((uri, RDF.type, genre_type))
        self.graph.add((uri, RDF.type, self.MOREO.FilmGenre))
        self.graph.add((uri, RDFS.label, Literal(name)))
        self.graph.add((uri, self.MOREO.has_name, Literal(name)))
        self.save()
        return uri

    def list_genres(self) -> list[dict]:
        from rdflib import OWL
        res = self.graph.query(LIST_GENRES, initNs={"moreo": self.MOREO, "owl": OWL})
        results = []
        for row in res:
            t_str = str(row[2]).split('#')[-1] if row[2] else "FilmGenre"
            results.append({
                "uri": str(row[0]),
                "name": str(row[1]) if row[1] else "",
                "type": t_str
            })
        return results
