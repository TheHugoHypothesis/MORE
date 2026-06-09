import unittest
import os
import sys
from rdflib import Graph, URIRef, RDF, Literal, XSD

# Add workspace root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ontology_manager import OntologyManager
from src.validation_engine import SHACLValidator

class TestSHACLValidationEngine(unittest.TestCase):
    def setUp(self):
        self.orig_rdf = "ontology/moreo_ontology.rdf"
        self.test_active_rdf = "data/active_ontology_val_test.rdf"
        
        # Remove any leftover test file
        if os.path.exists(self.test_active_rdf):
            os.remove(self.test_active_rdf)
            
        self.om = OntologyManager(base_rdf_path=self.orig_rdf, active_rdf_path=self.test_active_rdf)
        self.validator = SHACLValidator()

    def tearDown(self):
        if os.path.exists(self.test_active_rdf):
            os.remove(self.test_active_rdf)
        test_dir = os.path.dirname(self.test_active_rdf)
        if os.path.exists(test_dir) and not os.listdir(test_dir):
            os.rmdir(test_dir)

    def test_initial_graph_conforms(self):
        # O grafo original com ou sem o Pellet deve ser válido em relação ao SHACL
        conforms, report_text, errors = self.validator.validate_graph(self.om.graph)
        self.assertTrue(conforms, f"O grafo inicial deveria estar conforme. Erros: {report_text}")
        self.assertEqual(len(errors), 0)

    def test_missing_required_movie_properties(self):
        # Cria um filme incompleto inserindo triplas inválidas diretamente no grafo
        movie_uri = self.om.get_uri("Filme_Incompleto")
        
        # Apenas declaramos que é um Filme e Filme de Ficção, mas sem título, data, etc.
        self.om.graph.add((movie_uri, RDF.type, self.om.MOREO.Movie))
        self.om.graph.add((movie_uri, RDF.type, self.om.MOREO.FIctionMovie))
        
        conforms, report_text, errors = self.validator.validate_graph(self.om.graph)
        self.assertFalse(conforms, "Um filme sem título, datas, gênero e nacionalidade deveria falhar na validação SHACL.")
        self.assertGreater(len(errors), 0)
        
        # Verifica se as mensagens corretas definidas no SHACL estão nos erros
        messages = [e.message for e in errors]
        self.assertTrue(any("Todo filme deve ter exatamente um título" in msg for msg in messages))
        self.assertTrue(any("Todo filme deve ter exatamente uma data de produção" in msg for msg in messages))
        
        # Verifica se o focus_node aponta para o filme incompleto
        for err in errors:
            if "has_title" in str(err.path) or "has_production_date" in str(err.path):
                self.assertEqual(err.focus_node, str(movie_uri))

    def test_documentary_violation_only_director(self):
        # Documentários só podem conter DirectorRole, não ActorRole.
        # Criamos o gênero de documentário
        genre_uri = self.om.create_genre("Documentário Histórico", is_documentary=True)
        nat_uri = self.om.create_nation("Alemanha")
        dir_uri = self.om.create_person("Werner Herzog", 81, str(nat_uri), "Masculino")
        act_uri = self.om.create_person("Actor Exemplo", 40, str(nat_uri), "Masculino")
        
        # Criamos um documentário e vinculamos um Ator a ele.
        # Isso viola a restrição sh:class :DirectorRole para contains_role no DocumentaryShape.
        doc_uri = self.om.create_movie(
            title="Grizzly Man",
            production_date="2005-01-01",
            release_date="2005-08-12",
            language="Inglês",
            nationality_uri=str(nat_uri),
            genre_uris=[str(genre_uri)],
            director_person_uri=str(dir_uri),
            actor_person_uris=[str(act_uri)]  # Violador
        )
        
        conforms, report_text, errors = self.validator.validate_graph(self.om.graph)
        self.assertFalse(conforms, "Documentário com atores (ActorRole) deveria violar o SHACL.")
        
        messages = [e.message for e in errors]
        self.assertTrue(any("Um Documentário só pode conter papéis do tipo Diretor." in msg for msg in messages))

    def test_fiction_movie_violation_missing_actor(self):
        # Filme de Ficção deve conter pelo menos um Ator (ActorRole) em contains_role.
        genre_uri = self.om.create_genre("Suspense", is_documentary=False)
        nat_uri = self.om.create_nation("EUA")
        dir_uri = self.om.create_person("Alfred Hitchcock", 80, str(nat_uri), "Masculino")
        
        # Criamos um filme de ficção sem passar nenhum ator.
        # Isso viola a regra de qualifiedValueShape da FictionMovieShape.
        movie_uri = self.om.create_movie(
            title="Psicose",
            production_date="1960-01-01",
            release_date="1960-09-08",
            language="Inglês",
            nationality_uri=str(nat_uri),
            genre_uris=[str(genre_uri)],
            director_person_uri=str(dir_uri),
            actor_person_uris=[]  # Violação: nenhum ator
        )
        
        conforms, report_text, errors = self.validator.validate_graph(self.om.graph)
        self.assertFalse(conforms, "Filme de ficção sem ator deveria violar a restrição de contagem mínima de atores.")
        
        messages = [e.message for e in errors]
        self.assertTrue(any("Um Filme de Ficção deve conter pelo menos um Ator" in msg for msg in messages))
        
if __name__ == "__main__":
    unittest.main()
