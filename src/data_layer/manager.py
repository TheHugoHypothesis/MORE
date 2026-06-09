from .base import BaseOntologyManager
from .crud.nation import NationCrudMixin
from .crud.genre import GenreCrudMixin
from .crud.person import PersonCrudMixin
from .crud.user import UserCrudMixin
from .crud.movie import MovieCrudMixin
from .crud.rating import RatingCrudMixin
from .crud.award import AwardCrudMixin
from .exporters import ExporterMixin

class OntologyManager(
    BaseOntologyManager,
    NationCrudMixin,
    GenreCrudMixin,
    PersonCrudMixin,
    UserCrudMixin,
    MovieCrudMixin,
    RatingCrudMixin,
    AwardCrudMixin,
    ExporterMixin
):
    def __init__(self, base_rdf_path: str = "ontology/moreo_ontology.rdf", active_rdf_path: str = "data/active_ontology.rdf"):
        super().__init__(base_rdf_path=base_rdf_path, active_rdf_path=active_rdf_path)
