import os
from typing import List, Tuple
from rdflib import Graph
from pyshacl import validate
from .models import ValidationErrorDetail
from .parser import SHACLReportParser

class SHACLValidator:
    """
    Classe principal responsável por carregar os SHACL Shapes e validar
    grafos de dados RDFLib, retornando relatórios estruturados.
    """
    def __init__(self, shacl_path: str = "ontology/moreo_shacl.ttl"):
        self.shacl_path = os.path.abspath(shacl_path)
        if not os.path.exists(self.shacl_path):
            raise FileNotFoundError(f"Arquivo SHACL não encontrado em: {self.shacl_path}")
            
        self.shacl_graph = Graph()
        self.shacl_graph.parse(self.shacl_path, format="ttl")

    def validate_graph(self, data_graph: Graph, inference: str = "rdfs") -> Tuple[bool, str, List[ValidationErrorDetail]]:
        """
        Valida um rdflib.Graph contra as formas SHACL carregadas.
        
        Args:
            data_graph: O grafo RDF contendo os dados a serem validados.
            inference: Tipo de inferência a aplicar antes da validação (ex: 'rdfs', 'owlrl', 'none').
            
        Returns:
            Um tuple (conforms, report_text, errors_list) contendo:
            - conforms: boolean indicando se o grafo está conforme as regras.
            - report_text: string legível descrevendo o relatório do PySHACL.
            - errors_list: lista de objetos ValidationErrorDetail com erros estruturados.
        """
        # Executa validação pyshacl
        conforms, report_graph, report_text = validate(
            data_graph,
            shacl_graph=self.shacl_graph,
            inference=inference,
            serialize_results_format="ttl"
        )
        
        errors = []
        if not conforms:
            errors = SHACLReportParser.parse_report(report_graph)
            
        return conforms, report_text, errors
