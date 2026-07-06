# config.py
from pathlib import Path
from rdflib import Namespace

# --- DIRETÓRIOS E ARQUIVOS ---
BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / "ml-1m"
ONTO_BASE = BASE_DIR / "moreo_ontology.ttl"
ARQUIVO_SAIDA = BASE_DIR / "moreo_populado_1m.owl"
ARQUIVO_INFERIDO = BASE_DIR / "moreo_inferido_1m.owl"

# --- NAMESPACES ---
MOREO_URI = "http://www.semanticweb.org/ontologies/2026/3/MOREO#"
MOREO = Namespace(MOREO_URI)
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

# --- LIMITES DE DADOS (AMSTRAS DE DESENVOLVIMENTO) ---
LIMIT_MOVIES = 500
LIMIT_USERS = 500
LIMIT_RATINGS = 10000 # Massa crítica mínima exigida

# --- MAPAS ESTÁTICOS ---
MAPA_PROFISSOES = {
    0: "other or not specified", 1: "academic/educator", 2: "artist",
    3: "clerical/admin", 4: "college/grad student", 5: "customer service",
    6: "doctor/health care", 7: "executive/managerial", 8: "farmer",
    9: "homemaker", 10: "K-12 student", 11: "lawyer", 12: "programmer",
    13: "retired", 14: "sales/marketing", 15: "scientist", 16: "self-employed",
    17: "technician/engineer", 18: "tradesman/craftsman", 19: "unemployed", 20: "writer"
}

# --- CONFIGURAÇÕES DO WIKIDATA ---
WIKIDATA_BATCH_SIZE = 100
WIKIDATA_DELAY_BETWEEN_REQUESTS = 1.0  # Intervalo mínimo de tempo entre requisições com sucesso
WIKIDATA_MAX_RETRIES = 5               # Número máximo de tentativas em caso de erro 429 ou erros transitórios
WIKIDATA_DEFAULT_RETRY_SLEEP = 5.0     # Tempo padrão de espera se o cabeçalho Retry-After estiver ausente
WIKIDATA_USER_AGENT = "MoreoOntologyETL/4.0 (contact@yourdomain.org) Python-Requests"

