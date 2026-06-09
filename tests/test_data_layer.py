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

    def test_user_preferences_and_crud(self):
        # Pre-requisite genre and person for preferences
        genre_uri = self.om.create_genre("Sci-Fi", is_documentary=False)
        person_uri = self.om.create_person("Christopher Nolan", 53, str(self.om.create_nation("Reino Unido")), "Masculino")
        
        # Create User with initial preferences
        user_uri = self.om.create_user("test_prefs@example.com", phone="123456789", preferences=[str(genre_uri)])
        
        # Retrieve user
        user = self.om.get_user(str(user_uri))
        self.assertEqual(user["email"], "test_prefs@example.com")
        self.assertEqual(user["phone"], "123456789")
        self.assertIn(str(genre_uri), user["preferences"])
        self.assertNotIn(str(person_uri), user["preferences"])
        
        # Update user preferences
        success = self.om.update_user_preferences(str(user_uri), [str(genre_uri), str(person_uri)])
        self.assertTrue(success)
        
        # Re-fetch and verify update
        user_updated = self.om.get_user(str(user_uri))
        self.assertIn(str(genre_uri), user_updated["preferences"])
        self.assertIn(str(person_uri), user_updated["preferences"])
        self.assertEqual(len(user_updated["preferences"]), 2)

        # Non-existent entities behaviour
        self.assertEqual(self.om.get_user("http://example.org/nonexistent"), {})
        self.assertFalse(self.om.update_user_preferences("http://example.org/nonexistent", []))
        self.assertEqual(self.om.get_movie("http://example.org/nonexistent"), {})

    def test_movie_filtering(self):
        # Nations
        nat_br = self.om.create_nation("Brasil")
        nat_us = self.om.create_nation("EUA")
        
        # Genres
        genre_doc = self.om.create_genre("Cine Doc", is_documentary=True)
        genre_fic = self.om.create_genre("Aventura", is_documentary=False)
        
        # People
        dir_br = self.om.create_person("Diretor BR", 40, str(nat_br), "Masculino")
        dir_us = self.om.create_person("Diretor US", 45, str(nat_us), "Feminino")
        act_br = self.om.create_person("Ator BR", 35, str(nat_br), "Masculino")
        act_us = self.om.create_person("Ator US", 38, str(nat_us), "Feminino")
        
        # Movie 1 (Documentary, Brazilian)
        m1 = self.om.create_movie(
            title="Documentario BR",
            production_date="2020-01-01",
            release_date="2020-02-01",
            language="Português",
            nationality_uri=str(nat_br),
            genre_uris=[str(genre_doc)],
            director_person_uri=str(dir_br)
        )
        
        # Movie 2 (Fiction, American)
        m2 = self.om.create_movie(
            title="Aventura US",
            production_date="2021-01-01",
            release_date="2021-02-01",
            language="Inglês",
            nationality_uri=str(nat_us),
            genre_uris=[str(genre_fic)],
            director_person_uri=str(dir_us),
            actor_person_uris=[str(act_us)]
        )
        
        # Filter by genre
        movies_doc = self.om.list_movies(genre="Cine Doc")
        self.assertEqual(len(movies_doc), 1)
        self.assertEqual(movies_doc[0]["title"], "Documentario BR")
        
        # Filter by director
        movies_dir_us = self.om.list_movies(director="Diretor US")
        self.assertEqual(len(movies_dir_us), 1)
        self.assertEqual(movies_dir_us[0]["title"], "Aventura US")
        
        # Filter by actor
        movies_act_us = self.om.list_movies(actor="Ator US")
        self.assertEqual(len(movies_act_us), 1)
        self.assertEqual(movies_act_us[0]["title"], "Aventura US")
        
        # Filter by nationality
        movies_nat_br = self.om.list_movies(nationality="Brasil")
        self.assertEqual(len(movies_nat_br), 1)
        self.assertEqual(movies_nat_br[0]["title"], "Documentario BR")

    def test_global_rating_average(self):
        nat = self.om.create_nation("EUA")
        genre = self.om.create_genre("Ação", is_documentary=False)
        dir_uri = self.om.create_person("John Doe", 50, str(nat), "Masculino")
        
        movie_uri = self.om.create_movie(
            title="Action Movie",
            production_date="2025-01-01",
            release_date="2025-01-10",
            language="Inglês",
            nationality_uri=str(nat),
            genre_uris=[str(genre)],
            director_person_uri=str(dir_uri)
        )
        
        user1 = self.om.create_user("u1@rating.com")
        user2 = self.om.create_user("u2@rating.com")
        user3 = self.om.create_user("u3@rating.com")
        
        # Rate movie
        self.om.create_rating(str(user1), str(movie_uri), 5)
        self.om.create_rating(str(user2), str(movie_uri), 4)
        self.om.create_rating(str(user3), str(movie_uri), 3)
        
        # Check average rating
        movie = self.om.get_movie(str(movie_uri))
        self.assertAlmostEqual(movie["global_rating"], 4.0)
        
        # Invalid score range
        with self.assertRaises(ValueError):
            self.om.create_rating(str(user1), str(movie_uri), 6)
        with self.assertRaises(ValueError):
            self.om.create_rating(str(user1), str(movie_uri), 0)

    def test_awards_and_indications(self):
        nat = self.om.create_nation("Coreia do Sul")
        genre = self.om.create_genre("Suspense", is_documentary=False)
        dir_uri = self.om.create_person("Bong Joon-ho", 54, str(nat), "Masculino")
        
        movie_uri = self.om.create_movie(
            title="Parasite",
            production_date="2019-01-01",
            release_date="2019-05-30",
            language="Coreano",
            nationality_uri=str(nat),
            genre_uris=[str(genre)],
            director_person_uri=str(dir_uri)
        )
        
        # Create Award (Win) for Movie
        award_win = self.om.create_award(
            category="Melhor Filme",
            ceremony="Oscar",
            date_str="2020-02-09",
            movie_uri=str(movie_uri),
            is_winner=True
        )
        self.assertTrue(str(award_win).startswith(str(self.om.MOREO) + "Award_"))
        
        # Create Indication for Movie
        award_ind = self.om.create_award(
            category="Melhor Roteiro",
            ceremony="Oscar",
            date_str="2020-02-09",
            movie_uri=str(movie_uri),
            is_winner=False
        )
        
        # Verify awards listing
        awards = self.om.list_awards(movie_uri=str(movie_uri))
        self.assertEqual(len(awards), 2)
        
        winners = [a for a in awards if a["is_winner"]]
        nominees = [a for a in awards if not a["is_winner"]]
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0]["category"], "Melhor Filme")
        self.assertEqual(len(nominees), 1)
        self.assertEqual(nominees[0]["category"], "Melhor Roteiro")

    def test_pellet_reasoner(self):
        # Verify pellet runs on the temp active graph without error
        self.om.run_reasoner()

if __name__ == "__main__":
    unittest.main()
