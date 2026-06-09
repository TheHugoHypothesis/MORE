from typing import List
from rdflib import Graph, Namespace
from .models import ValidationErrorDetail

SH = Namespace("http://www.w3.org/ns/shacl#")

class SHACLReportParser:
    """
    Parser responsável por analisar o grafo de resultados gerado pelo PySHACL
    e extrair os detalhes das violações de forma estruturada.
    """
    @staticmethod
    def parse_report(report_graph: Graph) -> List[ValidationErrorDetail]:
        query = """
        SELECT ?focusNode ?resultPath ?resultMessage ?resultSeverity ?sourceConstraint
        WHERE {
            ?result a sh:ValidationResult ;
                    sh:focusNode ?focusNode .
            OPTIONAL { ?result sh:resultPath ?resultPath }
            OPTIONAL { ?result sh:resultMessage ?resultMessage }
            OPTIONAL { ?result sh:resultSeverity ?resultSeverity }
            OPTIONAL { ?result sh:sourceConstraintComponent ?sourceConstraint }
        }
        """
        results = report_graph.query(query, initNs={"sh": SH})
        errors = []
        for row in results:
            focus_node = str(row[0]) if row[0] else ""
            path = str(row[1]) if row[1] else ""
            message = str(row[2]) if row[2] else ""
            
            # Extrai o nome local da URI da severidade e da restrição (ex: Violation, DatatypeConstraintComponent)
            severity = str(row[3]).split("#")[-1] if row[3] else "Violation"
            severity = severity.split("/")[-1] # fallback para slash URIs
            
            constraint = str(row[4]).split("#")[-1] if row[4] else ""
            constraint = constraint.split("/")[-1]
            
            errors.append(ValidationErrorDetail(
                focus_node=focus_node,
                path=path,
                message=message,
                severity=severity,
                constraint=constraint
            ))
        return errors
