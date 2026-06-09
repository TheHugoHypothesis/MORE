from rdflib import URIRef, Literal, RDF, RDFS, XSD, Namespace
from ..queries import LIST_PERSONS

class PersonCrudMixin:
    def create_person(self, name: str, age: int, nationality_uri: str, gender: str) -> URIRef:
        uri = self.get_uri(name)
        if (uri, RDF.type, self.MOREO.Person) in self.graph:
            return uri
            
        self.graph.add((uri, RDF.type, self.MOREO.Person))
        self.graph.add((uri, RDFS.label, Literal(name)))
        self.graph.add((uri, self.MOREO.has_name, Literal(name)))
        self.graph.add((uri, self.MOREO.has_age, Literal(age, datatype=XSD.integer)))
        self.graph.add((uri, self.MOREO.has_nationality, URIRef(nationality_uri)))
        
        # Link Gender using DOLCE schema
        DOLCE = Namespace("https://w3id.org/DOLCE/OWL/DOLCEbasic#")
        clean_n = self.clean_name(name)
        g_qual = self.get_uri(f"Gender_{clean_n}")
        g_reg = self.get_uri(f"GenderRegion_{clean_n}")
        
        self.graph.add((g_qual, RDF.type, self.MOREO.GenderQuality))
        self.graph.add((g_qual, DOLCE.directQualityOf, uri))
        
        self.graph.add((g_reg, RDF.type, self.MOREO.GenderRegion))
        self.graph.add((g_reg, DOLCE.constantQualeOf, g_qual))
        self.graph.add((g_reg, self.MOREO.has_gender_label, Literal(gender)))
        
        self.save()
        return uri

    def list_persons(self) -> list[dict]:
        res = self.execute_query(LIST_PERSONS)
        results = []
        for row in res:
            results.append({
                "uri": str(row[0]),
                "name": str(row[1]) if row[1] else "",
                "age": int(row[2]) if row[2] else 0,
                "nationality_uri": str(row[3]) if row[3] else "",
                "nationality": str(row[4]) if row[4] else "",
                "gender": str(row[5]) if row[5] else ""
            })
        return results
