from .base import BaseOntologyManager
from .entities_crud import EntityCrudMixin
from .movie_crud import MovieCrudMixin
from .rating_award_crud import RatingAwardCrudMixin
from .exporters import ExporterMixin

class OntologyManager(
    BaseOntologyManager,
    EntityCrudMixin,
    MovieCrudMixin,
    RatingAwardCrudMixin,
    ExporterMixin
):
    def __init__(self, base_rdf_path: str = "ontology/moreo_ontology.rdf", active_rdf_path: str = "data/active_ontology.rdf"):
        super().__init__(base_rdf_path=base_rdf_path, active_rdf_path=active_rdf_path)
