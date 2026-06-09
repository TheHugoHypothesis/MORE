from rdflib import URIRef, Literal, RDF, RDFS, XSD, Namespace

class EntityCrudMixin:
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
        query = """
        SELECT DISTINCT ?uri ?name ?type WHERE {
            ?uri a moreo:FilmGenre .
            OPTIONAL { ?uri moreo:has_name ?name }
            OPTIONAL {
                ?uri a ?type .
                FILTER (?type != moreo:FilmGenre && ?type != owl:Class)
            }
        } ORDER BY ?name
        """
        from rdflib import OWL
        res = self.graph.query(query, initNs={"moreo": self.MOREO, "owl": OWL})
        results = []
        for row in res:
            t_str = str(row[2]).split('#')[-1] if row[2] else "FilmGenre"
            results.append({
                "uri": str(row[0]),
                "name": str(row[1]) if row[1] else "",
                "type": t_str
            })
        return results

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
        DOLCE = Namespace("https://w3id.org/DOLCE/OWL/DOLCEbasic#")
        query = """
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
        res = self.graph.query(query, initNs={"moreo": self.MOREO, "dolce": DOLCE, "rdfs": RDFS})
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

    def create_user(self, email: str, phone: str = None, preferences: list[str] = None) -> URIRef:
        clean_email = email.replace("@", "_").replace(".", "_")
        uri = self.get_uri(f"User_{clean_email}")
        if (uri, RDF.type, self.MOREO.User) in self.graph:
            return uri
            
        self.graph.add((uri, RDF.type, self.MOREO.User))
        self.graph.add((uri, RDFS.label, Literal(email)))
        self.graph.add((uri, self.MOREO.has_email, Literal(email)))
        if phone:
            self.graph.add((uri, self.MOREO.has_phone, Literal(phone)))
            
        if preferences:
            for p in preferences:
                self.graph.add((uri, self.MOREO.has_preference, URIRef(p)))
                
        self.save()
        return uri

    def list_users(self) -> list[dict]:
        query = """
        SELECT DISTINCT ?uri ?email ?phone WHERE {
            ?uri a moreo:User .
            OPTIONAL { ?uri moreo:has_email ?email }
            OPTIONAL { ?uri moreo:has_phone ?phone }
        } ORDER BY ?email
        """
        res = self.graph.query(query, initNs={"moreo": self.MOREO})
        results = []
        for row in res:
            uri = row[0]
            email = str(row[1]) if row[1] else ""
            phone = str(row[2]) if row[2] else ""
            
            # Fetch preferences
            prefs = [str(p) for p in self.graph.objects(uri, self.MOREO.has_preference)]
            results.append({
                "uri": str(uri),
                "email": email,
                "phone": phone,
                "preferences": prefs
            })
        return results

    def get_user(self, user_uri: str) -> dict:
        user_ref = URIRef(user_uri)
        if (user_ref, RDF.type, self.MOREO.User) not in self.graph:
            return {}
            
        email = str(self.graph.value(user_ref, self.MOREO.has_email) or "")
        phone = str(self.graph.value(user_ref, self.MOREO.has_phone) or "")
        prefs = [str(p) for p in self.graph.objects(user_ref, self.MOREO.has_preference)]
        
        return {
            "uri": user_uri,
            "email": email,
            "phone": phone,
            "preferences": prefs
        }

    def update_user_preferences(self, user_uri: str, preferences: list[str]) -> bool:
        user_ref = URIRef(user_uri)
        if (user_ref, RDF.type, self.MOREO.User) not in self.graph:
            return False
            
        # Remove old preferences
        self.graph.remove((user_ref, self.MOREO.has_preference, None))
        
        # Add new preferences
        for p in preferences:
            self.graph.add((user_ref, self.MOREO.has_preference, URIRef(p)))
            
        self.save()
        return True
