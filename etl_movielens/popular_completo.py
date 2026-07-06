import config
import wikidata_service

config.LIMIT_MOVIES = 3883
config.LIMIT_USERS = 6040
config.LIMIT_RATINGS = 1000209

original_exec = wikidata_service._executar_consulta_sparql
query_counter = 0

def logged_exec(query):
    global query_counter
    query_counter += 1
    print(f"[LOG] Executando consulta SPARQL no Wikidata (Lote #{query_counter})...")
    res = original_exec(query)
    if res:
        print(f"[LOG] Lote #{query_counter} processado com sucesso.")
    else:
        print(f"[LOG] Lote #{query_counter} falhou ou retornou vazio.")
    return res

wikidata_service._executar_consulta_sparql = logged_exec

original_paises = wikidata_service.buscar_paises_em_lote
def logged_paises(lista):
    print("[LOG] Iniciando enriquecimento de paises via Wikidata...")
    res = original_paises(lista)
    print(f"[LOG] Enriquecimento de paises concluido. Total mapeado: {len(res)}")
    return res
wikidata_service.buscar_paises_em_lote = logged_paises

original_diretores = wikidata_service.buscar_diretores_em_lote
def logged_diretores(lista):
    print("[LOG] Iniciando enriquecimento de diretores via Wikidata...")
    res = original_diretores(lista)
    print(f"[LOG] Enriquecimento de diretores concluido. Total mapeado: {len(res)}")
    return res
wikidata_service.buscar_diretores_em_lote = logged_diretores

original_atores = wikidata_service.buscar_atores_em_lote
def logged_atores(lista):
    print("[LOG] Iniciando enriquecimento de atores via Wikidata...")
    res = original_atores(lista)
    print(f"[LOG] Enriquecimento de atores concluido. Total mapeado: {len(res)}")
    return res
wikidata_service.buscar_atores_em_lote = logged_atores

original_premios_filmes = wikidata_service.buscar_premios_filmes_em_lote
def logged_premios_filmes(lista):
    print("[LOG] Iniciando enriquecimento de premios de filmes via Wikidata...")
    res = original_premios_filmes(lista)
    print(f"[LOG] Enriquecimento de premios de filmes concluido. Total mapeado: {len(res)}")
    return res
wikidata_service.buscar_premios_filmes_em_lote = logged_premios_filmes

original_premios_pessoas = wikidata_service.buscar_premios_pessoas_em_lote
def logged_premios_pessoas(lista):
    print("[LOG] Iniciando enriquecimento de premios de pessoas via Wikidata...")
    res = original_premios_pessoas(lista)
    print(f"[LOG] Enriquecimento de premios de pessoas concluido. Total mapeado: {len(res)}")
    return res
wikidata_service.buscar_premios_pessoas_em_lote = logged_premios_pessoas

from rdflib import Graph
import etl_processors
from main import calcular_e_exibir_metricas

def main():
    g = Graph()
    g.parse(str(config.ONTO_BASE), format="turtle")
    g.bind("moreo", config.MOREO)
    g.bind("wd", config.WIKIDATA)

    filmes_ids = etl_processors.processar_filmes(g)

    etl_processors.enriquecer_via_wikidata(g, filmes_ids)
    etl_processors.enriquecer_diretores_via_wikidata(g, filmes_ids)
    etl_processors.enriquecer_atores_via_wikidata(g, filmes_ids)
    etl_processors.enriquecer_premios_filmes_via_wikidata(g, filmes_ids)
    etl_processors.enriquecer_premios_pessoas_via_wikidata(g, filmes_ids)

    usuarios_ids = etl_processors.processar_usuarios(g)
    etl_processors.processar_avaliacoes(g, usuarios_ids, filmes_ids)

    arquivo_saida = config.BASE_DIR / "moreo_populado_completo.owl"
    g.serialize(destination=str(arquivo_saida), format="xml")

    calcular_e_exibir_metricas(g, "Populado Completo (Sem Inferencia)")

if __name__ == "__main__":
    main()
