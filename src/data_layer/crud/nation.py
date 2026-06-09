from rdflib import URIRef, Literal, RDF, RDFS
from ..queries import LIST_NATIONS

class NationCrudMixin:
    def create_nation(self, name: str) -> URIRef:
        uri = self.get_uri(name)
        if (uri, RDF.type, self.MOREO.Nation) in self.graph:
            return uri
        self.graph.add((uri, RDF.type, self.MOREO.Nation))
        self.graph.add((uri, RDFS.label, Literal(name)))
        self.save()
        return uri

    def list_nations(self) -> list[dict]:
        res = self.graph.query(LIST_NATIONS, initNs={"moreo": self.MOREO, "rdfs": RDFS})
        return [{"uri": str(row[0]), "name": str(row[1]) if row[1] else ""} for row in res]
