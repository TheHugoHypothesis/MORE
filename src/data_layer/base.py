import os
import re
import datetime
import tempfile
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD
import owlready2
from owlready2 import get_ontology, onto_path, sync_reasoner_pellet, declare_datatype

# Register XSD.dateTimeStamp globally in rdflib and owlready2
rdflib.term.bind(XSD.dateTimeStamp, datetime.datetime.fromisoformat)

def _parser_datetime_stamp(val):
    return datetime.datetime.fromisoformat(val)

def _unparser_datetime_stamp(val):
    return val.isoformat()

# Register dateTimeStamp in owlready2 before any ontology is loaded
try:
    declare_datatype(datetime.datetime, XSD.dateTimeStamp, _parser_datetime_stamp, _unparser_datetime_stamp)
except Exception:
    pass

class BaseOntologyManager:
    def __init__(self, base_rdf_path: str = "ontology/moreo_ontology.rdf", active_rdf_path: str = "data/active_ontology.rdf"):
        self.base_rdf_path = os.path.abspath(base_rdf_path)
        self.active_rdf_path = os.path.abspath(active_rdf_path)
        self.ontology_dir = os.path.dirname(self.base_rdf_path)
        self.rdf_path = self.base_rdf_path  # for compatibility
        
        # Namespaces
        self.MOREO = Namespace("http://www.semanticweb.org/ontologies/2026/3/MOREO#")
        
        # Initialize RDFLib graph
        self.graph = Graph()
        self.load()
        
    def load(self):
        if os.path.exists(self.active_rdf_path):
            self.graph.parse(self.active_rdf_path, format="xml")
        else:
            self.graph.parse(self.base_rdf_path, format="xml")
        
    def save(self):
        os.makedirs(os.path.dirname(self.active_rdf_path), exist_ok=True)
        self.graph.serialize(self.active_rdf_path, format="xml")
        
    def run_reasoner(self):
        # We need to run pellet via owlready2
        with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as tmp:
            tmp_path = tmp.name
            self.graph.serialize(tmp_path, format="xml")
            
        try:
            if self.ontology_dir not in onto_path:
                onto_path.append(self.ontology_dir)
                
            # Create a dedicated owlready2 World
            world = owlready2.World()
            
            # Map the Dolce namespace to the local file to avoid network calls
            dolce_local_path = os.path.join(self.ontology_dir, "DOLCEbasicOWL.owl")
            if os.path.exists(dolce_local_path):
                try:
                    world.get_ontology("https://w3id.org/DOLCE/OWL/DOLCEbasic/3.5").load(
                        only_local=True,
                        fileobj=open(dolce_local_path, "rb")
                    )
                except Exception as e:
                    print(f"Warning mapping DOLCE: {e}")
                    
            # Load ontology from temp OWL file
            onto = world.get_ontology(f"file://{tmp_path}").load()
            
            # Run Pellet reasoner
            with onto:
                sync_reasoner_pellet(
                    infer_property_values=True,
                    infer_data_property_values=True
                )
                
            # Synchronize inferred recommendations back to RDFLib graph
            for m in onto.individuals():
                if hasattr(m, "is_recommended_for"):
                    for u in m.is_recommended_for:
                        self.graph.add((URIRef(m.iri), self.MOREO.is_recommended_for, URIRef(u.iri)))
                        
                if hasattr(m, "has_preference"):
                    for pref in m.has_preference:
                        self.graph.add((URIRef(m.iri), self.MOREO.has_preference, URIRef(pref.iri)))
            
            self.save()
            world.close()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    def clean_name(self, name: str) -> str:
        # Replaces spaces and special chars with underscores
        clean = re.sub(r"[^\w\s-]", "", name)
        clean = re.sub(r"[\s-]+", "_", clean).strip("_")
        return clean
        
    def get_uri(self, name: str) -> URIRef:
        return URIRef(self.MOREO + self.clean_name(name))

    def execute_query(self, query_str: str, bindings: dict = None) -> list:
        from rdflib import RDFS, OWL, RDF
        init_ns = {
            "moreo": self.MOREO,
            "dolce": Namespace("https://w3id.org/DOLCE/OWL/DOLCEbasic#"),
            "rdfs": RDFS,
            "rdf": RDF,
            "owl": OWL
        }
        return list(self.graph.query(query_str, initNs=init_ns, initBindings=bindings))
