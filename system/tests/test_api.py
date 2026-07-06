import unittest
import os
import sys
import tempfile
import shutil
import rdflib
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_path = os.path.join(project_root, "ontology", "moreo_populado_1m.owl")
        
        fd, cls.temp_path = tempfile.mkstemp(suffix=".owl")
        os.close(fd)
        shutil.copy(source_path, cls.temp_path)
        
        main.DATA_PATH = cls.temp_path
        main.graph_cache.clear()
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_path):
            os.remove(cls.temp_path)

    def test_register_user_success(self):
        payload = {
            "user_id": "test_user_success_999",
            "email": "jane.doe@example.com",
            "name": "Jane Doe",
            "age": 28,
            "gender": "Female",
            "nationality": "Brazil",
            "phone": "+5511999999999"
        }
        response = self.client.post("/users", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("user_uri", response.json())
        
        g = rdflib.Graph()
        g.parse(self.temp_path, format="xml")
        moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
        rdf = rdflib.RDF
        user_uri = moreo["USER_test_user_success_999"]
        self.assertTrue((user_uri, rdf.type, moreo.User) in g)

    def test_register_user_duplicate(self):
        payload = {
            "user_id": "test_user_dup_999",
            "email": "dup@example.com",
            "name": "Dup User",
            "age": 28,
            "gender": "Female",
            "nationality": "Brazil"
        }
        response = self.client.post("/users", json=payload)
        self.assertEqual(response.status_code, 200)
        
        response2 = self.client.post("/users", json=payload)
        self.assertEqual(response2.status_code, 400)

    def test_register_user_invalid_email(self):
        payload = {
            "user_id": "test_user_invalid_888",
            "email": "invalid-email-format",
            "name": "Invalid User",
            "age": 28,
            "gender": "Female",
            "nationality": "Brazil"
        }
        response = self.client.post("/users", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_submit_rating_success(self):
        user_payload = {
            "user_id": "test_user_rating_777",
            "email": "user777@example.com",
            "name": "User 777",
            "age": 30,
            "gender": "Male",
            "nationality": "United States"
        }
        self.client.post("/users", json=user_payload)
        
        rating_payload = {
            "user_id": "test_user_rating_777",
            "movie_id": "MOVIE_387",
            "score": 5,
            "timestamp": "2026-06-14T12:00:00Z"
        }
        response = self.client.post("/ratings", json=rating_payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("rating_uri", response.json())
        
        g = rdflib.Graph()
        g.parse(self.temp_path, format="xml")
        moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
        rdf = rdflib.RDF
        user_uri = moreo["USER_test_user_rating_777"]
        rating_triples = list(g.triples((user_uri, moreo.performs_rating, None)))
        self.assertGreater(len(rating_triples), 0)

    def test_submit_rating_invalid_user(self):
        rating_payload = {
            "user_id": "non_existent_user_abc",
            "movie_id": "MOVIE_387",
            "score": 5
        }
        response = self.client.post("/ratings", json=rating_payload)
        self.assertEqual(response.status_code, 404)

    def test_submit_rating_invalid_movie(self):
        user_payload = {
            "user_id": "test_user_rating_invalid_mov",
            "email": "usermov@example.com",
            "name": "User Mov",
            "age": 30,
            "gender": "Male",
            "nationality": "United States"
        }
        self.client.post("/users", json=user_payload)
        
        rating_payload = {
            "user_id": "test_user_rating_invalid_mov",
            "movie_id": "NonExistentMovie",
            "score": 5
        }
        response = self.client.post("/ratings", json=rating_payload)
        self.assertEqual(response.status_code, 404)

    def test_submit_rating_invalid_score(self):
        user_payload = {
            "user_id": "test_user_rating_invalid_score",
            "email": "userscore@example.com",
            "name": "User Score",
            "age": 30,
            "gender": "Male",
            "nationality": "United States"
        }
        self.client.post("/users", json=user_payload)
        
        rating_payload = {
            "user_id": "test_user_rating_invalid_score",
            "movie_id": "MOVIE_387",
            "score": 6
        }
        response = self.client.post("/ratings", json=rating_payload)
        self.assertEqual(response.status_code, 422)

    def test_register_user_with_preferences(self):
        payload = {
            "user_id": "test_user_pref_888",
            "email": "pref.user@example.com",
            "name": "Pref User",
            "age": 32,
            "gender": "Male",
            "nationality": "Brazil",
            "preferred_awards": ["http://www.semanticweb.org/ontologies/2026/3/MOREO#AWARD_480_Q393686"],
            "preferred_genres": ["http://www.semanticweb.org/ontologies/2026/3/MOREO#GENRE_Adventure"],
            "preferred_directors": ["http://www.semanticweb.org/ontologies/2026/3/MOREO#PERSON_Q63069"],
            "preferred_actors": ["http://www.semanticweb.org/ontologies/2026/3/MOREO#PERSON_Q15794601"]
        }
        response = self.client.post("/users", json=payload)
        self.assertEqual(response.status_code, 200)
        
        g = rdflib.Graph()
        g.parse(self.temp_path, format="xml")
        moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
        user_uri = moreo["USER_test_user_pref_888"]
        
        pref_triples = list(g.triples((user_uri, moreo.has_preference, None)))
        self.assertEqual(len(pref_triples), 4)

    def test_get_preferences_endpoints(self):
        response = self.client.get("/awards")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        
        response = self.client.get("/genres")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        
        response = self.client.get("/directors")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        
        response = self.client.get("/actors")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

if __name__ == "__main__":
    unittest.main()
