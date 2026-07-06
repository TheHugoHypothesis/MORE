import unittest
import rdflib
import sys
import os
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.semantic.validation import validate_ontology
from src.semantic.recommendation import gerar_recomendacao_usuario, obter_recomendacao_semantica_rapida

class TestSemanticLayer(unittest.TestCase):
    def test_validate_ontology_real_shacl(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shacl_path = os.path.join(project_root, "ontology", "moreo_shacl.ttl")
        
        g = rdflib.Graph()
        moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
        rdf = rdflib.RDF
        xsd = rdflib.XSD
        
        movie = moreo.Movie_1
        g.add((movie, rdf.type, moreo.Movie))
        g.add((movie, moreo.has_language, rdflib.Literal("en", datatype=xsd.string)))
        g.add((movie, moreo.has_production_date, rdflib.Literal("2026-06-14T12:00:00", datatype=xsd.dateTime)))
        g.add((movie, moreo.has_release_date, rdflib.Literal("2026-06-14T12:00:00", datatype=xsd.dateTime)))
        g.add((movie, moreo.has_title, rdflib.Literal("Test Movie", datatype=xsd.string)))
        
        genre = moreo.Genre_1
        g.add((genre, rdf.type, moreo.FilmGenre))
        g.add((genre, moreo.has_name, rdflib.Literal("Action", datatype=xsd.string)))
        g.add((genre, moreo.is_genre_of, movie))
        g.add((movie, moreo.has_genre, genre))
        
        nation = moreo.Nation_1
        g.add((nation, rdf.type, moreo.Nation))
        g.add((nation, moreo.is_nationality_of, movie))
        g.add((movie, moreo.has_nationality, nation))
        
        person = moreo.Person_1
        g.add((person, rdf.type, moreo.Person))
        g.add((person, moreo.has_name, rdflib.Literal("Director Name", datatype=xsd.string)))
        g.add((person, moreo.has_age, rdflib.Literal(45, datatype=xsd.positiveInteger)))
        g.add((person, moreo.has_nationality, nation))
        
        quality = moreo.Quality_1
        g.add((quality, rdf.type, moreo.GenderQuality))
        g.add((quality, moreo.direct_quality_of, person))
        g.add((person, moreo.has_quality, quality))
        
        region = moreo.Region_1
        g.add((region, rdf.type, moreo.GenderRegion))
        g.add((region, moreo.constant_quale_of, quality))
        g.add((region, moreo.has_gender_label, rdflib.Literal("Male", datatype=xsd.string)))
        
        role = moreo.Role_1
        g.add((role, rdf.type, moreo.DirectorRole))
        g.add((role, moreo.is_role_of, person))
        g.add((role, moreo.is_played_in, movie))
        g.add((movie, moreo.contains_role, role))
        
        fd, temp_path = tempfile.mkstemp(suffix=".ttl")
        os.close(fd)
        try:
            g.serialize(destination=temp_path, format="ttl")
            conforms, report = validate_ontology(temp_path, shacl_path)
            self.assertTrue(conforms)
        finally:
            os.remove(temp_path)

    def test_gerar_recomendacao_usuario(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ontology_path = os.path.join(project_root, "ontology", "moreo_ontology.ttl")
        query_path = os.path.join(project_root, "sparql", "subgraph.sparql")
        
        moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
        rdf = rdflib.RDF
        xsd = rdflib.XSD
        
        g = rdflib.Graph()
        user = moreo.USER_76
        g.add((user, rdf.type, moreo.User))
        g.add((user, moreo.has_email, rdflib.Literal("user76@example.com", datatype=xsd.string)))
        
        movie = moreo.Movie_1
        g.add((movie, rdf.type, moreo.Movie))
        g.add((movie, moreo.has_title, rdflib.Literal("Movie One", datatype=xsd.string)))
        g.add((movie, moreo.has_production_date, rdflib.Literal("2026-06-14T12:00:00", datatype=xsd.dateTime)))
        g.add((movie, moreo.has_release_date, rdflib.Literal("2026-06-14T12:00:00", datatype=xsd.dateTime)))
        
        rating = moreo.Rating_1
        g.add((rating, rdf.type, moreo.UserRating))
        g.add((rating, moreo.is_about, movie))
        g.add((rating, moreo.is_performed_by, user))
        g.add((rating, moreo.has_score, rdflib.Literal(5, datatype=xsd.nonNegativeInteger)))
        g.add((rating, moreo.has_timestamp, rdflib.Literal("2026-06-14T12:00:00Z", datatype=xsd.dateTimeStamp)))
        g.add((user, moreo.performs_rating, rating))
        
        recs = gerar_recomendacao_usuario(g, ontology_path, query_path, "76")
        self.assertIsInstance(recs, list)

    def test_obter_recomendacao_semantica_rapida(self):
        moreo = rdflib.Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
        rdf = rdflib.RDF
        xsd = rdflib.XSD
        
        g = rdflib.Graph()
        user = moreo.USER_76
        g.add((user, rdf.type, moreo.User))
        
        movie = moreo.Movie_1
        g.add((movie, rdf.type, moreo.Movie))
        
        # Test Global Rating > 4.5
        gr = moreo.GlobalRating_1
        g.add((gr, rdf.type, moreo.GlobalRating))
        g.add((gr, moreo.is_global_rating_quality_of, movie))
        g.add((gr, moreo.has_average_score, rdflib.Literal(4.8, datatype=xsd.float)))
        
        recs = obter_recomendacao_semantica_rapida(g, str(user))
        self.assertIn(str(movie), recs)

if __name__ == "__main__":
    unittest.main()
