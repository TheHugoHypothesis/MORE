from rdflib import URIRef, Literal, RDF, RDFS

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
        query = """
        SELECT DISTINCT ?uri ?name WHERE {
            ?uri a moreo:Nation .
            OPTIONAL { ?uri rdfs:label ?name }
        } ORDER BY ?name
        """
        res = self.graph.query(query, initNs={"moreo": self.MOREO, "rdfs": RDFS})
        return [{"uri": str(row[0]), "name": str(row[1]) if row[1] else ""} for row in res]
