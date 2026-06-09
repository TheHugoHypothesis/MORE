from rdflib import URIRef, Literal, RDF, RDFS
from ..queries import LIST_USERS

class UserCrudMixin:
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
        res = self.graph.query(LIST_USERS, initNs={"moreo": self.MOREO})
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
