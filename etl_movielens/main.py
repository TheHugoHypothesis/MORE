import owlready2
import traceback
from rdflib import Graph, RDF
import config
import etl_processors

def calcular_e_exibir_metricas(g, label):
    total_triples = len(g)
    distinct_relations = len(set(g.predicates()))
    
    user_count = len(list(g.subjects(RDF.type, config.MOREO.User)))
    movie_count = len(list(g.subjects(RDF.type, config.MOREO.Movie)))
    rating_count = len(list(g.subjects(RDF.type, config.MOREO.UserRating)))
    
    # Busca todas as classes que pertencem ao namespace MOREO
    classes = set(g.objects(predicate=RDF.type))
    moreo_classes = sorted({c for c in classes if str(c).startswith(config.MOREO_URI)})
    
    other_count = sum(
        len(list(g.subjects(RDF.type, c))) 
        for c in moreo_classes 
        if str(c) not in [str(config.MOREO.User), str(config.MOREO.Movie), str(config.MOREO.UserRating)]
    )
    
    print(f"\n==========================================")
    print(f" MÉTRICAS DO GRAFO ({label})")
    print(f"==========================================")
    print(f"Total de Triplas (Arestas RDF): {total_triples:,}".replace(",", "."))
    print(f"Tipos de Relações Distintas (Predicados): {distinct_relations:,}".replace(",", "."))
    print(f"Instâncias de Usuários (User): {user_count:,}".replace(",", "."))
    print(f"Instâncias de Filmes (Movie): {movie_count:,}".replace(",", "."))
    print(f"Instâncias de Avaliações (UserRating): {rating_count:,}".replace(",", "."))
    print(f"Instâncias de Outras Entidades: {other_count:,}".replace(",", "."))
    
    print("\nDetalhamento por Classe MOREO:")
    print("-" * 50)
    for c in moreo_classes:
        class_name = str(c).replace(config.MOREO_URI, "")
        cnt = len(list(g.subjects(RDF.type, c)))
        print(f" {class_name:<35} | {cnt:>10,}".replace(",", "."))
    print("-" * 50)
    
    def fmt(val):
        return f"{val:,}".replace(",", ".")
        
    latex = f"""\\begin{{table}}[ht]
\\centering
\\caption{{Métricas do Grafo de Conhecimento MOREO ({label})}}
\\label{{tab:ETL_{label.replace(" ", "_").lower()}}}
\\begin{{tabular}}{{lr}}
\\toprule
\\textbf{{Métrica do Grafo de Conhecimento (MOREO)}} & \\textbf{{Quantidade}} \\\\
\\midrule
Instâncias de Usuários (User) & {fmt(user_count)} \\\\
Instâncias de Filmes (Movie) & {fmt(movie_count)} \\\\
Instâncias de Avaliações (UserRating) & {fmt(rating_count)} \\\\
Instâncias de Outras Entidades (Person, Award, etc.) & {fmt(other_count)} \\\\
Triplas Relacionais Totais (Arestas RDF) & {fmt(total_triples)} \\\\
Tipos de Relações Distintas ($R$) & {fmt(distinct_relations)} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""
    print("\nCódigo LaTeX gerado:")
    print(latex)
    print("==========================================\n")

def run_pipeline():
    print("Iniciando o pipeline de ETL Semantico Modular para MovieLens 1M...")

    # Configura o Grafo e carrega a estrutura base (TBox)
    g = Graph()
    g.parse(str(config.ONTO_BASE), format="turtle")
    g.bind("moreo", config.MOREO)
    g.bind("wd", config.WIKIDATA)

    filmes_ids = etl_processors.processar_filmes(g)

    # Enriquecimento externo (Wikidata)
    etl_processors.enriquecer_via_wikidata(g, filmes_ids)
    etl_processors.enriquecer_diretores_via_wikidata(g, filmes_ids)
    etl_processors.enriquecer_atores_via_wikidata(g, filmes_ids)
    etl_processors.enriquecer_premios_filmes_via_wikidata(g, filmes_ids)
    etl_processors.enriquecer_premios_pessoas_via_wikidata(g, filmes_ids)

    #  Processa Usuários e Avaliações locais
    usuarios_ids = etl_processors.processar_usuarios(g)
    etl_processors.processar_avaliacoes(g, usuarios_ids, filmes_ids)

    print(f"Gravando base de conhecimento povoada em RDF/XML: {config.ARQUIVO_SAIDA.name}...")
    g.serialize(destination=str(config.ARQUIVO_SAIDA), format="xml")
    print("Pipeline de ETL e Enriquecimento concluido com sucesso!")

    # Exibe as métricas pré-inferência
    calcular_e_exibir_metricas(g, "Pré-inferência")

    print("\nCarregando dados no Owlready2 para inferencia...")
    mundo = owlready2.World()

    try:
        mundo.get_ontology(f"file://{config.ARQUIVO_SAIDA.resolve()}").load()

        print("Disparando o Raciocinador Pellet Leve...")
        owlready2.reasoning.JAVA_MEMORY = 40000
        owlready2.sync_reasoner_pellet(x=mundo, infer_property_values=True, debug=2)
        print("Raciocinio logico concluido sem inconsistencias!")

        print(f"Salvando grafo inferido final em: {config.ARQUIVO_INFERIDO.name}...")
        mundo.save(file=str(config.ARQUIVO_INFERIDO), format="rdfxml")
        print("Processo finalizado com sucesso absoluto!")

        # Exibe as métricas pós-inferência
        print("Carregando o grafo pós-inferência para cálculo de métricas...")
        g_post = Graph()
        g_post.parse(str(config.ARQUIVO_INFERIDO), format="xml")
        calcular_e_exibir_metricas(g_post, "Pós-inferência")

    except Exception:
        print("\n[ERRO] Falha detectada na etapa de inferencia logica:")
        traceback.print_exc()

if __name__ == "__main__":
    run_pipeline()
