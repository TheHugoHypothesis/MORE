import io
from pathlib import Path
from owlready2 import World, sync_reasoner_pellet, onto_path
from rdflib import Graph, URIRef, Literal, RDF, XSD

BASE_DIR = Path(__file__).parent
CQ_DIR = BASE_DIR / "SPARQL Competency Questions"
ARQUIVO_ONTOLOGIA = BASE_DIR / "moreo_ontology.ttl"
ARQUIVO_DOLCE = BASE_DIR / "DOLCEbasic-3.5.owl"
MOREO_URI = "http://www.semanticweb.org/ontologies/2026/3/MOREO#"

onto_path.append(str(BASE_DIR))

mundo_teste = World()

if ARQUIVO_DOLCE.exists():
    mundo_teste.get_ontology("https://w3id.org/DOLCE/OWL/DOLCEbasic/3.5/").imported_ontologies.append(
        mundo_teste.get_ontology(str(ARQUIVO_DOLCE)).load()
    )
else:
    print(f"AVISO: O arquivo de dependência {ARQUIVO_DOLCE.name} não foi encontrado na pasta!")

g_base = Graph()
g_base.parse(str(ARQUIVO_ONTOLOGIA), format="turtle")

def ns(fragmento):
    return URIRef(f"{MOREO_URI}{fragmento}")

# Definição dos tipos dos indivíduos (Classes)
triplas_teste = [
    (ns("USER123"), RDF.type, ns("User")),
    (ns("PERSON123"), RDF.type, ns("Person")),
    (ns("NATION_BR"), RDF.type, ns("Nation")),
    (ns("NATION_US"), RDF.type, ns("Nation")),

    (ns("ATOR_SELTON"), RDF.type, ns("ActorRole")),
    (ns("ATOR_AVENGERS"), RDF.type, ns("ActorRole")),
    (ns("DIRETOR_CHICO"), RDF.type, ns("DirectorRole")),
    (ns("DIRETOR_AVENGERS"), RDF.type, ns("DirectorRole")),
    (ns("DIRETOR_SENNA"), RDF.type, ns("DirectorRole")),

    (ns("MOVIE999"), RDF.type, ns("Movie")),
    (ns("MOVIE_AVENGERS"), RDF.type, ns("Movie")),
    (ns("MOVIE_DOC1"), RDF.type, ns("Movie")),

    # Alinhamento das classes de Gêneros
    (ns("GENRE_COMEDY"), RDF.type, ns("FilmGenre")),
    (ns("GENRE_COMEDY"), RDF.type, ns("FictionGenre")),

    (ns("GENRE_DOCUMENTARY"), RDF.type, ns("FilmGenre")),
    (ns("GENRE_DOCUMENTARY"), RDF.type, ns("DocumentaryGenre")),

    (ns("RATING555"), RDF.type, ns("UserRating")),
    (ns("CELEBRITY_SELTON"), RDF.type, ns("Person")),
    (ns("ROLE_CHICO"), RDF.type, ns("Role")),
    (ns("GLOBAL_RATING_BR"), RDF.type, ns("GlobalRating")),
    (ns("AWARD_OSCAR"), RDF.type, ns("Award")),

    # Relações de Objeto (Object Properties)
    (ns("USER123"), ns("has_person_identity"), ns("PERSON123")),
    (ns("PERSON123"), ns("has_nationality"), ns("NATION_BR")),

    # Nacionalidades
    (ns("MOVIE999"), ns("has_nationality"), ns("NATION_BR")),
    (ns("MOVIE_AVENGERS"), ns("has_nationality"), ns("NATION_US")),
    (ns("MOVIE_DOC1"), ns("has_nationality"), ns("NATION_BR")),

    # Conectando papéis obrigatórios aos filmes para o Pellet
    (ns("MOVIE999"), ns("contains_role"), ns("DIRETOR_CHICO")),
    (ns("MOVIE_AVENGERS"), ns("contains_role"), ns("DIRETOR_AVENGERS")),
    (ns("MOVIE_DOC1"), ns("contains_role"), ns("DIRETOR_SENNA")),

    (ns("MOVIE999"), ns("contains_role"), ns("ATOR_SELTON")),
    (ns("MOVIE_AVENGERS"), ns("contains_role"), ns("ATOR_AVENGERS")),

    # Preferências
    (ns("USER123"), ns("has_preference"), ns("GENRE_COMEDY")),
    (ns("USER123"), ns("has_preference"), ns("CELEBRITY_SELTON")),
    (ns("USER123"), ns("has_preference"), ns("AWARD_OSCAR")),

    # Gêneros
    (ns("MOVIE999"), ns("has_genre"), ns("GENRE_COMEDY")),
    (ns("MOVIE_AVENGERS"), ns("has_genre"), ns("GENRE_COMEDY")),
    (ns("MOVIE_DOC1"), ns("has_genre"), ns("GENRE_DOCUMENTARY")),

    (ns("USER123"), ns("performs_rating"), ns("RATING555")),
    (ns("RATING555"), ns("is_about"), ns("MOVIE999")),
    (ns("ROLE_CHICO"), ns("is_role_of"), ns("CELEBRITY_SELTON")),
    (ns("ROLE_CHICO"), ns("is_played_in"), ns("MOVIE999")),
    (ns("GLOBAL_RATING_BR"), ns("is_global_rating_quality_of"), ns("MOVIE999")),
    (ns("AWARD_OSCAR"), ns("is_award_of"), ns("MOVIE999")),

    (ns("MOVIE999"), ns("has_production_date"), Literal("2000-09-10T00:00:00", datatype=XSD.dateTime)),
    (ns("MOVIE_AVENGERS"), ns("has_production_date"), Literal("2012-04-11T00:00:00", datatype=XSD.dateTime)),
    (ns("MOVIE_DOC1"), ns("has_production_date"), Literal("2010-11-12T00:00:00", datatype=XSD.dateTime)),

    # Valores Literais
    (ns("PERSON123"), ns("has_name"), Literal("João Grilo", datatype=XSD.string)),
    (ns("MOVIE999"), ns("has_title"), Literal("O Auto da Compadecida", datatype=XSD.string)),
    (ns("MOVIE_AVENGERS"), ns("has_title"), Literal("The Avengers", datatype=XSD.string)),
    (ns("MOVIE_DOC1"), ns("has_title"), Literal("Senna", datatype=XSD.string)),
    (ns("RATING555"), ns("has_score"), Literal(5, datatype=XSD.integer)),
    (ns("GLOBAL_RATING_BR"), ns("has_average_score"), Literal(4.8, datatype=XSD.float)),
    (ns("AWARD_OSCAR"), ns("has_category_name"), Literal("Melhor Filme", datatype=XSD.string)),
    (ns("AWARD_OSCAR"), ns("has_award_date"), Literal("2026-03-20T20:00:00", datatype=XSD.dateTime)),
    (ns("ATOR_SELTON"), ns("is_role_of"), ns("CELEBRITY_SELTON")),
    (ns("ATOR_SELTON"), ns("is_played_in"), ns("MOVIE999")),

    (ns("ATOR_AVENGERS"), ns("is_played_in"), ns("MOVIE_AVENGERS"))
]

for s, p, o in triplas_teste:
    g_base.add((s, p, o))

rdf_xml_data = g_base.serialize(format="xml")
onto = mundo_teste.get_ontology(MOREO_URI).load(
    fileobj=io.BytesIO(rdf_xml_data.encode("utf-8"))
)

sync_reasoner_pellet(x=mundo_teste, infer_property_values=True, infer_data_property_values=True)

arquivo_dump = BASE_DIR / "cenario_teste.ttl"
mundo_teste.save(file=str(arquivo_dump), format="rdfxml")

g = mundo_teste.as_rdflib_graph()

for s, p, o in g.triples((None, RDF.type, None)):
    if "FictionGenre" in str(o):
        print("FictionGenre existe no grafo:", s, o)

# --- CONFIGURAÇÃO E EXECUÇÃO DAS VALIDAÇÕES SPARQL ---
testes_config = {
    "cq1.sparql": [
        {"movie": f"{MOREO_URI}MOVIE999"},
        {"movie": f"{MOREO_URI}MOVIE_AVENGERS"}
    ],
    "cq2.sparql": [{"genre": f"{MOREO_URI}GENRE_COMEDY"}],
    "cq3.sparql": [{"movie": f"{MOREO_URI}MOVIE999"}],
    "cq4.sparql": [{"movie": f"{MOREO_URI}MOVIE999", "title": "O Auto da Compadecida", "averageScore": "4.8"}],
    "cq5.sparql": [{"movie": f"{MOREO_URI}MOVIE999", "title": "O Auto da Compadecida", "award": f"{MOREO_URI}AWARD_OSCAR", "categoryName": "Melhor Filme"}],
    "cq6.sparql": [
        {"movie": f"{MOREO_URI}MOVIE999", "title": "O Auto da Compadecida", "sameNationality": "true"},
        {"movie": f"{MOREO_URI}MOVIE_DOC1", "title": "Senna", "sameNationality": "true"}, # Alterado para true
        {"movie": f"{MOREO_URI}MOVIE_AVENGERS", "title": "The Avengers", "sameNationality": "false"}
    ],
    "cq7.sparql": [{"person": f"{MOREO_URI}PERSON123", "name": "João Grilo"}],
    "cq8.sparql": [{"movie": f"{MOREO_URI}MOVIE999", "title": "O Auto da Compadecida", "categoryName": "Melhor Filme", "awardDate": "2026-03-20T20:00:00"}],

    "cq9.sparql": [
        {
            "movie": f"{MOREO_URI}MOVIE_DOC1",
            "title": "Senna",
            "inferredClass": f"{MOREO_URI}Documentary"
        },
        {
            "movie": f"{MOREO_URI}MOVIE999",
            "title": "O Auto da Compadecida",
            "inferredClass": f"{MOREO_URI}FictionMovie"
        },
        {
            "movie": f"{MOREO_URI}MOVIE_AVENGERS",
            "title": "The Avengers",
            "inferredClass": f"{MOREO_URI}FictionMovie"
        }
    ],
    "cq10.sparql": [{"rating": f"{MOREO_URI}RATING555", "score": "5"}]
}

def rodar_validacao(nome_arquivo, esperado):
    caminho_cq = CQ_DIR / nome_arquivo
    if not caminho_cq.exists():
        print(f"{nome_arquivo}: ARQUIVO NAO ENCONTRADO")
        return

    with open(caminho_cq, "r", encoding="utf-8") as file:
        query_sparql = file.read()

    try:
        resultados = g.query(query_sparql)
        obtido = []
        for row in resultados:
            obtido.append({str(k): str(v) for k, v in row.asdict().items()})

        obtido_filtrado = []
        for item in obtido:
            item_filtrado = {k: v for k, v in item.items() if k in esperado[0]}
            if item_filtrado:
                obtido_filtrado.append(item_filtrado)

        sucesso = True
        for esp in esperado:
            if esp not in obtido_filtrado:
                sucesso = False
                break

        if len(obtido_filtrado) != len(esperado):
            sucesso = False

        if sucesso:
            print(f"{nome_arquivo}: PASS")
        else:
            print(f"{nome_arquivo}: FAIL")
            print(f"  Esperado: {esperado}")
            print(f"  Obtido:   {obtido_filtrado}")

    except Exception as e:
        print(f"{nome_arquivo}: ERROR ({str(e)})")

for arquivo, esperado in sorted(testes_config.items()):
    rodar_validacao(arquivo, esperado)
