import unittest
import os
import sys

# Add workspace root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ontology_manager import OntologyManager

class TestDataLayer(unittest.TestCase):
    def setUp(self):
        self.orig_rdf = "ontology/moreo_ontology.rdf"
        self.test_active_rdf = "data/active_ontology_test.rdf"
        
        # Ensure clean state by removing previous test active file if exists
        if os.path.exists(self.test_active_rdf):
            os.remove(self.test_active_rdf)
            
        # Instantiate manager with base ontology and the temporary test active path
        self.om = OntologyManager(base_rdf_path=self.orig_rdf, active_rdf_path=self.test_active_rdf)

    def tearDown(self):
        # Remove temporary test active file
        if os.path.exists(self.test_active_rdf):
            os.remove(self.test_active_rdf)
            
        # Also clean up the data/ directory if it is empty
        test_dir = os.path.dirname(self.test_active_rdf)
        if os.path.exists(test_dir) and not os.listdir(test_dir):
            os.rmdir(test_dir)

    def test_nation_crud(self):
        # Create Nation
        uri = self.om.create_nation("Brasil")
        self.assertTrue(str(uri).endswith("Brasil"))
        
        # List and verify
        nations = self.om.list_nations()
        names = [n["name"] for n in nations]
        self.assertIn("Brasil", names)

    def test_genre_crud(self):
        # Create Fiction Genre
        uri_f = self.om.create_genre("Drama", is_documentary=False)
        self.assertTrue(str(uri_f).endswith("Drama"))
        
        # Create Documentary Genre
        uri_d = self.om.create_genre("Histórico", is_documentary=True)
        self.assertTrue(str(uri_d).endswith("Histórico"))
        
        genres = self.om.list_genres()
        names = {g["name"]: g["type"] for g in genres}
        self.assertIn("Drama", names)
        self.assertEqual(names["Drama"], "FictionGenre")
        self.assertIn("Histórico", names)
        self.assertEqual(names["Histórico"], "DocumentaryGenre")

    def test_person_crud(self):
        # Pre-requisite nation
        nat_uri = self.om.create_nation("Brasil")
        
        # Create Person
        uri = self.om.create_person("Fernanda Montenegro", 96, str(nat_uri), "Feminino")
        self.assertTrue(str(uri).endswith("Fernanda_Montenegro"))
        
        persons = self.om.list_persons()
        person_names = [p["name"] for p in persons]
        self.assertIn("Fernanda Montenegro", person_names)

    def test_movie_and_rating_crud(self):
        # Pre-requisites
        nat_uri = self.om.create_nation("Brasil")
        genre_uri = self.om.create_genre("Drama", is_documentary=False)
        dir_uri = self.om.create_person("Walter Salles", 69, str(nat_uri), "Masculino")
        act_uri = self.om.create_person("Fernanda Montenegro", 96, str(nat_uri), "Feminino")
        
        # Create Movie
        movie_uri = self.om.create_movie(
            title="Central do Brasil",
            production_date="1998-01-01",
            release_date="1998-04-03",
            language="Português",
            nationality_uri=str(nat_uri),
            genre_uris=[str(genre_uri)],
            director_person_uri=str(dir_uri),
            actor_person_uris=[str(act_uri)]
        )
        self.assertTrue(str(movie_uri).endswith("Central_do_Brasil"))
        
        # Get and verify movie
        movie = self.om.get_movie(str(movie_uri))
        self.assertEqual(movie["title"], "Central do Brasil")
        self.assertEqual(movie["language"], "Português")
        self.assertEqual(len(movie["actors"]), 1)
        self.assertEqual(movie["actors"][0]["name"], "Fernanda Montenegro")
        
        # Create User and Rating
        user_uri = self.om.create_user("user1@test.com")
        self.assertTrue(str(user_uri).endswith("User_user1_test_com"))
        
        rating_uri = self.om.create_rating(str(user_uri), str(movie_uri), 5)
        self.assertTrue(str(rating_uri).startswith(str(self.om.MOREO) + "UserRating_"))
        
        # Verify rating list
        ratings = self.om.get_user_ratings(str(user_uri))
        self.assertEqual(len(ratings), 1)
        self.assertEqual(ratings[0]["score"], 5)
        self.assertEqual(ratings[0]["movie_title"], "Central do Brasil")
        
        # Verify matrix and PyKEEN exports
        matrix = self.om.get_rating_matrix()
        self.assertFalse(matrix.empty)
        
        triples = self.om.export_triples_for_pykeen()
        self.assertGreater(len(triples), 0)

    def test_pellet_reasoner(self):
        # Verify pellet runs on the temp active graph without error
        self.om.run_reasoner()

if __name__ == "__main__":
    unittest.main()
