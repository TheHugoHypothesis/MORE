import datetime
from rdflib import URIRef, Literal, RDF, XSD
from ..queries import LIST_AWARDS

class AwardCrudMixin:
    def create_award(
        self,
        category: str,
        ceremony: str,
        date_str: str,  # YYYY-MM-DD
        movie_uri: str = None,
        role_uri: str = None,
        is_winner: bool = True
    ) -> URIRef:
        # Generate unique URI for Award
        clean_cat = self.clean_name(category)
        clean_cer = self.clean_name(ceremony)
        clean_date = date_str.replace("-", "")
        
        target_name = ""
        if movie_uri:
            target_name = URIRef(movie_uri).split('#')[-1]
        elif role_uri:
            target_name = URIRef(role_uri).split('#')[-1]
            
        award_uri = self.get_uri(f"Award_{clean_cer}_{clean_cat}_{clean_date}_{target_name}")
        
        # Add to graph
        self.graph.add((award_uri, RDF.type, self.MOREO.Award))
        self.graph.add((award_uri, self.MOREO.has_category_name, Literal(category)))
        self.graph.add((award_uri, self.MOREO.has_ceremony_name, Literal(ceremony)))
        
        # Date as xsd:dateTimeStamp in UTC (Pellet requirement)
        dt_stamp = f"{date_str}T00:00:00+00:00"
        self.graph.add((award_uri, self.MOREO.has_award_date, Literal(dt_stamp, datatype=XSD.dateTimeStamp)))
        
        # Link relations
        prop_rel = self.MOREO.is_award_of if is_winner else self.MOREO.is_indication_of
        
        if movie_uri:
            self.graph.add((award_uri, prop_rel, URIRef(movie_uri)))
        if role_uri:
            self.graph.add((award_uri, prop_rel, URIRef(role_uri)))
            
        self.save()
        return award_uri

    def list_awards(self, movie_uri: str = None, ceremony: str = None) -> list[dict]:
        res = self.execute_query(LIST_AWARDS)
        results = []
        for row in res:
            uri_str = str(row[0])
            m_uri = str(row[4]) if row[4] else ""
            r_uri = str(row[5]) if row[5] else ""
            
            # Filters
            if movie_uri and m_uri != movie_uri:
                continue
            if ceremony and str(row[2]) != ceremony:
                continue
                
            results.append({
                "uri": uri_str,
                "category": str(row[1]),
                "ceremony": str(row[2]),
                "date": str(row[3]).split('T')[0] if row[3] else "",
                "movie_uri": m_uri,
                "role_uri": r_uri,
                "is_winner": bool(row[6])
            })
        return results
