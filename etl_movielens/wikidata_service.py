import time
import random
import requests
import config

def _executar_consulta_sparql(query):
    """
    Executa uma consulta SPARQL no Wikidata com tratamento de rate limit (429),
    cabeçalhos de compressão e política de retentativa/backoff exponencial.
    """
    endpoint_url = "https://query.wikidata.org/sparql"
    
    headers = {
        'User-Agent': config.WIKIDATA_USER_AGENT,
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate'
    }
    
    retries = 0
    while retries < config.WIKIDATA_MAX_RETRIES:
        try:
            response = requests.get(
                endpoint_url,
                params={'format': 'json', 'query': query},
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                # Respeita o delay configurado entre requisições bem-sucedidas
                if config.WIKIDATA_DELAY_BETWEEN_REQUESTS > 0:
                    time.sleep(config.WIKIDATA_DELAY_BETWEEN_REQUESTS)
                return response.json()
                
            elif response.status_code == 429:
                # Respeita o cabeçalho Retry-After se fornecido, senão usa o padrão
                retry_after_str = response.headers.get("Retry-After")
                sleep_time = config.WIKIDATA_DEFAULT_RETRY_SLEEP
                if retry_after_str:
                    try:
                        sleep_time = float(retry_after_str)
                    except ValueError:
                        pass
                
                # Adiciona jitter para evitar sincronização de requisições
                sleep_time += random.uniform(0.1, 1.0)
                print(f"[WIKIDATA] Erro 429: Rate limit atingido. Aguardando {sleep_time:.2f} segundos antes de tentar novamente...")
                time.sleep(sleep_time)
                retries += 1
                
            elif response.status_code in [500, 502, 503, 504]:
                # Backoff exponencial simples com jitter para erros do servidor
                sleep_time = (2 ** retries) + random.uniform(0.5, 1.5)
                print(f"[WIKIDATA] Erro {response.status_code}: Servidor instável. Tentando novamente em {sleep_time:.2f} segundos...")
                time.sleep(sleep_time)
                retries += 1
                
            else:
                print(f"[WIKIDATA] Erro irrecuperável HTTP {response.status_code}. Cancelando consulta.")
                break
                
        except (requests.exceptions.RequestException, Exception) as e:
            # Backoff exponencial simples com jitter para erros de conexão ou timeout
            sleep_time = (2 ** retries) + random.uniform(0.5, 1.5)
            print(f"[WIKIDATA] Erro de rede/timeout ({e}). Tentando novamente em {sleep_time:.2f} segundos...")
            time.sleep(sleep_time)
            retries += 1
            
    print(f"[WIKIDATA] Falha ao executar consulta após {retries} tentativas.")
    return None

def _obter_itens_unicos(lista):
    """
    Remove itens duplicados com base na combinação de título e ano.
    """
    vistos = set()
    unicos = []
    for item in lista:
        chave = (item['titulo'], item['ano'])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)
    return unicos

def _chunk_lista(lista, chunk_size):
    """
    Divide a lista em sublistas de tamanho menor ou igual a chunk_size.
    """
    for i in range(0, len(lista), chunk_size):
        yield lista[i:i + chunk_size]

def buscar_paises_em_lote(lista_filmes):
    if not lista_filmes:
        return {}

    lista_unica = _obter_itens_unicos(lista_filmes)
    resultado_mapa = {}

    for chunk in _chunk_lista(lista_unica, config.WIKIDATA_BATCH_SIZE):
        linhas_values = []
        for f in chunk:
            titulo_escapado = f['titulo'].replace('"', '\\"')
            linhas_values.append(f'("{titulo_escapado}"@en "{f["ano"]}")')

        bloco_values = "\n        ".join(linhas_values)

        query = f"""
        SELECT ?searchTitle ?searchYear ?movie ?country ?countryLabel WHERE {{
          VALUES (?searchTitle ?searchYear) {{
            {bloco_values}
          }}

          ?movie rdfs:label ?searchTitle.
          ?movie wdt:P31/wdt:P279* wd:Q11424.
          ?movie wdt:P577 ?date.
          FILTER(CONTAINS(STR(?date), ?searchYear))
          ?movie wdt:P495 ?country.

          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        dados_json = _executar_consulta_sparql(query)
        if dados_json:
            bindings = dados_json.get("results", {}).get("bindings", [])
            for b in bindings:
                chave = f"{b['searchTitle']['value']}_{b['searchYear']['value']}"
                resultado_mapa[chave] = {
                    "movie_url": b["movie"]["value"],
                    "country_url": b["country"]["value"],
                    "country_label": b["countryLabel"]["value"]
                }
    return resultado_mapa

def buscar_diretores_em_lote(lista_filmes):
    if not lista_filmes:
        return {}

    lista_unica = _obter_itens_unicos(lista_filmes)
    resultado_mapa = {}

    for chunk in _chunk_lista(lista_unica, config.WIKIDATA_BATCH_SIZE):
        linhas_values = []
        for f in chunk:
            titulo_escapado = f['titulo'].replace('"', '\\"')
            linhas_values.append(f'("{titulo_escapado}"@en "{f["ano"]}")')

        bloco_values = "\n        ".join(linhas_values)

        query = f"""
        SELECT ?searchTitle ?searchYear ?movie ?director ?directorLabel ?country ?countryLabel ?birthDate WHERE {{
          VALUES (?searchTitle ?searchYear) {{
            {bloco_values}
          }}

          ?movie rdfs:label ?searchTitle.
          ?movie wdt:P31/wdt:P279* wd:Q11424.
          ?movie wdt:P577 ?date.
          FILTER(CONTAINS(STR(?date), ?searchYear))

          ?movie wdt:P57 ?director.

          OPTIONAL {{ ?director wdt:P27 ?country . }}
          OPTIONAL {{ ?director wdt:P569 ?birthDate . }}

          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        dados_json = _executar_consulta_sparql(query)
        if dados_json:
            bindings = dados_json.get("results", {}).get("bindings", [])
            for b in bindings:
                chave = f"{b['searchTitle']['value']}_{b['searchYear']['value']}"
                if chave not in resultado_mapa:
                    resultado_mapa[chave] = []

                diretor_info = {
                    "director_url": b["director"]["value"]
                }

                if "directorLabel" in b:
                    diretor_info["director_label"] = b["directorLabel"]["value"]
                if "country" in b and "countryLabel" in b:
                    diretor_info["country_url"] = b["country"]["value"]
                    diretor_info["country_label"] = b["countryLabel"]["value"]
                if "birthDate" in b:
                    diretor_info["birth_date"] = b["birthDate"]["value"]

                resultado_mapa[chave].append(diretor_info)
    return resultado_mapa

def buscar_atores_em_lote(lista_filmes):
    if not lista_filmes:
        return {}

    lista_unica = _obter_itens_unicos(lista_filmes)
    resultado_mapa = {}

    for chunk in _chunk_lista(lista_unica, config.WIKIDATA_BATCH_SIZE):
        linhas_values = []
        for f in chunk:
            titulo_escapado = f['titulo'].replace('"', '\\"')
            linhas_values.append(f'("{titulo_escapado}"@en "{f["ano"]}")')

        bloco_values = "\n        ".join(linhas_values)

        query = f"""
        SELECT ?searchTitle ?searchYear ?movie ?actor ?actorLabel ?country ?countryLabel ?birthDate WHERE {{
          VALUES (?searchTitle ?searchYear) {{
            {bloco_values}
          }}

          ?movie rdfs:label ?searchTitle.
          ?movie wdt:P31/wdt:P279* wd:Q11424.
          ?movie wdt:P577 ?date.
          FILTER(CONTAINS(STR(?date), ?searchYear))

          {{ ?movie wdt:P161 ?actor . }}
          UNION
          {{ ?movie wdt:P725 ?actor . }}

          OPTIONAL {{ ?actor wdt:P27 ?country . }}
          OPTIONAL {{ ?actor wdt:P569 ?birthDate . }}

          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        dados_json = _executar_consulta_sparql(query)
        if dados_json:
            bindings = dados_json.get("results", {}).get("bindings", [])
            for b in bindings:
                chave = f"{b['searchTitle']['value']}_{b['searchYear']['value']}"
                if chave not in resultado_mapa:
                    resultado_mapa[chave] = []

                ator_info = {
                    "actor_url": b["actor"]["value"]
                }

                if "actorLabel" in b:
                    ator_info["actor_label"] = b["actorLabel"]["value"]
                if "country" in b and "countryLabel" in b:
                    ator_info["country_url"] = b["country"]["value"]
                    ator_info["country_label"] = b["countryLabel"]["value"]
                if "birthDate" in b:
                    ator_info["birth_date"] = b["birthDate"]["value"]

                resultado_mapa[chave].append(ator_info)
    return resultado_mapa

def buscar_premios_filmes_em_lote(lista_busca):
    if not lista_busca:
        return {}

    lista_unica = _obter_itens_unicos(lista_busca)
    mapa_resultados = {}

    for chunk in _chunk_lista(lista_unica, config.WIKIDATA_BATCH_SIZE):
        linhas_values = []
        for item in chunk:
            titulo_escapado = item['titulo'].replace('"', '\\"')
            linhas_values.append(f'("{titulo_escapado}"@en "{item["ano"]}")')

        bloco_values = "\n        ".join(linhas_values)

        query = f"""
        SELECT ?searchTitle ?searchYear ?award_url ?award_urlLabel ?pointInTime ?eventLabel ?status WHERE {{
          VALUES (?searchTitle ?searchYear) {{
            {bloco_values}
          }}

          ?movie rdfs:label ?searchTitle.
          ?movie wdt:P31/wdt:P279* wd:Q11424.
          ?movie wdt:P577 ?date.
          FILTER(CONTAINS(STR(?date), ?searchYear))

          {{
            ?movie p:P166 ?awardStatement .
            BIND("won" AS ?status)
          }} UNION {{
            ?movie p:P1411 ?awardStatement .
            BIND("nominated" AS ?status)
          }}

          ?awardStatement (ps:P166|ps:P1411) ?award_url .

          OPTIONAL {{ ?awardStatement pq:P585 ?pointInTime . }}
          OPTIONAL {{ ?awardStatement pq:P805 ?event . }}

          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        dados_json = _executar_consulta_sparql(query)
        if dados_json:
            for binding in dados_json.get("results", {}).get("bindings", []):
                t = binding["searchTitle"]["value"]
                y = binding["searchYear"]["value"]
                chave = f"{t}_{y}"

                if chave not in mapa_resultados:
                    mapa_resultados[chave] = []

                premio = {
                    "award_url": binding["award_url"]["value"],
                    "status": binding["status"]["value"]
                }
                if "award_urlLabel" in binding:
                    premio["awardLabel"] = binding["award_urlLabel"]["value"]
                if "pointInTime" in binding:
                    premio["pointInTime"] = binding["pointInTime"]["value"]
                if "eventLabel" in binding:
                    premio["eventLabel"] = binding["eventLabel"]["value"]

                mapa_resultados[chave].append(premio)
    return mapa_resultados

def buscar_premios_pessoas_em_lote(lista_busca):
    if not lista_busca:
        return {}

    lista_unica = _obter_itens_unicos(lista_busca)
    mapa_resultados = {}

    for chunk in _chunk_lista(lista_unica, config.WIKIDATA_BATCH_SIZE):
        linhas_values = []
        for item in chunk:
            titulo_escapado = item['titulo'].replace('"', '\\"')
            linhas_values.append(f'("{titulo_escapado}"@en "{item["ano"]}")')

        bloco_values = "\n        ".join(linhas_values)

        query = f"""
        SELECT ?searchTitle ?searchYear ?person_url ?personRole ?award_url ?award_urlLabel ?pointInTime ?eventLabel ?status WHERE {{
          VALUES (?searchTitle ?searchYear) {{
            {bloco_values}
          }}

          ?movie rdfs:label ?searchTitle.
          ?movie wdt:P31/wdt:P279* wd:Q11424.
          ?movie wdt:P577 ?date.
          FILTER(CONTAINS(STR(?date), ?searchYear))

          {{
            ?movie wdt:P161 ?person_url .
            BIND("actor" AS ?personRole)
          }} UNION {{
            ?movie wdt:P57 ?person_url .
            BIND("director" AS ?personRole)
          }}

          {{
            ?person_url p:P166 ?awardStatement .
            BIND("won" AS ?status)
          }} UNION {{
            ?person_url p:P1411 ?awardStatement .
            BIND("nominated" AS ?status)
          }}

          ?awardStatement (ps:P166|ps:P1411) ?award_url .
          ?awardStatement pq:P1686 ?movie .

          OPTIONAL {{ ?awardStatement pq:P585 ?pointInTime . }}
          OPTIONAL {{ ?awardStatement pq:P805 ?event . }}

          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        dados_json = _executar_consulta_sparql(query)
        if dados_json:
            for binding in dados_json.get("results", {}).get("bindings", []):
                t = binding["searchTitle"]["value"]
                y = binding["searchYear"]["value"]
                chave = f"{t}_{y}"

                if chave not in mapa_resultados:
                    mapa_resultados[chave] = []

                premio = {
                    "person_url": binding["person_url"]["value"],
                    "personRole": binding["personRole"]["value"],
                    "award_url": binding["award_url"]["value"],
                    "status": binding["status"]["value"]
                }
                if "award_urlLabel" in binding:
                    premio["awardLabel"] = binding["award_urlLabel"]["value"]
                if "pointInTime" in binding:
                    premio["pointInTime"] = binding["pointInTime"]["value"]
                if "eventLabel" in binding:
                    premio["eventLabel"] = binding["eventLabel"]["value"]

                mapa_resultados[chave].append(premio)
    return mapa_resultados
