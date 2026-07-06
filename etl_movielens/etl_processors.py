import pandas as pd
import re
from datetime import datetime
from rdflib import URIRef, Literal, RDF, XSD
import config
import wikidata_service

def processar_filmes(g):
    print(f"Processing the first {config.LIMIT_MOVIES} movies...")
    movies_df = pd.read_csv(
        config.DATASET_DIR / "movies.dat",
        sep="::", engine="python", encoding="ISO-8859-1",
        names=["MovieID", "Title", "Genres"]
    ).head(config.LIMIT_MOVIES)

    filmes_ids = set()

    for _, row in movies_df.iterrows():
        mid = str(row["MovieID"])
        title = row["Title"]

        movie_uri = URIRef(f"{config.MOREO_URI}MOVIE_{mid}")
        g.add((movie_uri, RDF.type, config.MOREO.Movie))
        g.add((movie_uri, config.MOREO.has_title, Literal(title, datatype=XSD.string)))

        try:
            year_str = title.split("(")[-1].replace(")", "").strip()
            if year_str.isdigit():
                date_iso = f"{year_str}-01-01T00:00:00"
                g.add((movie_uri, config.MOREO.has_production_date, Literal(date_iso, datatype=XSD.dateTime)))
        except Exception:
            g.add((movie_uri, config.MOREO.has_production_date, Literal("2000-01-01T00:00:00", datatype=XSD.dateTime)))

        genres = row["Genres"].split("|")
        for g_name in genres:
            g_clean = g_name.replace("-", "").replace("'", "").replace(" ", "")
            genre_uri = URIRef(f"{config.MOREO_URI}GENRE_{g_clean}")
            g.add((genre_uri, RDF.type, config.MOREO.FilmGenre))
            g.add((movie_uri, config.MOREO.has_genre, genre_uri))

        filmes_ids.add(mid)

    return list(filmes_ids)

def processar_usuarios(g):
    print(f"Processing the first {config.LIMIT_USERS} users...")
    users_df = pd.read_csv(
        config.DATASET_DIR / "users.dat",
        sep="::", engine="python", encoding="ISO-8859-1",
        names=["UserID", "Gender", "Age", "Occupation", "Zip-code"]
    ).head(config.LIMIT_USERS)

    usuarios_ids = set()

    # Define Estados Unidos (USA) como Nation para associar aos usuários locais
    nation_usa_uri = URIRef(f"{config.MOREO_URI}NATION_Q30")
    g.add((nation_usa_uri, RDF.type, config.MOREO.Nation))
    g.add((nation_usa_uri, config.MOREO.has_name, Literal("United States", datatype=XSD.string)))
    g.add((nation_usa_uri, config.OWL.sameAs, URIRef("http://www.wikidata.org/entity/Q30")))

    for _, row in users_df.iterrows():
        uid = str(row["UserID"])
        user_uri = URIRef(f"{config.MOREO_URI}USER_{uid}")
        person_identity_uri = URIRef(f"{config.MOREO_URI}PERSON_{uid}")

        g.add((user_uri, RDF.type, config.MOREO.User))
        g.add((person_identity_uri, RDF.type, config.MOREO.Person))
        g.add((user_uri, config.MOREO.has_person_identity, person_identity_uri))
        g.add((user_uri, config.MOREO.has_email, Literal(f"user{uid}@movielens.org", datatype=XSD.string)))
        g.add((person_identity_uri, config.MOREO.has_nationality, nation_usa_uri))

        gender_quality = URIRef(f"{config.MOREO_URI}GENDER_QUALITY_{uid}")
        gender_region = URIRef(f"{config.MOREO_URI}GENDER_REGION_{uid}")

        g.add((gender_quality, RDF.type, config.MOREO.GenderQuality))
        g.add((gender_region, RDF.type, config.MOREO.GenderRegion))
        g.add((gender_quality, config.MOREO.direct_quality_of, person_identity_uri))
        g.add((gender_region, config.MOREO.constant_quale_of, gender_quality))

        label_genero = "Male" if row["Gender"] == "M" else "Female"
        g.add((gender_region, config.MOREO.has_gender_label, Literal(label_genero, datatype=XSD.string)))

        g.add((person_identity_uri, config.MOREO.has_age, Literal(int(row["Age"]), datatype=XSD.integer)))

        profissao_str = config.MAPA_PROFISSOES.get(int(row["Occupation"]), "other or not specified")
        g.add((person_identity_uri, config.MOREO.has_occupation, Literal(profissao_str, datatype=XSD.string)))

        usuarios_ids.add(uid)

    return list(usuarios_ids)

def processar_avaliacoes(g, usuarios_ids, filmes_ids):
    print("Processing ratings...")

    ratings_df = pd.read_csv(
        config.DATASET_DIR / "ratings.dat",
        sep="::", engine="python", encoding="ISO-8859-1",
        names=["UserID", "MovieID", "Rating", "Timestamp"]
    )

    usuarios_ids_set = set(usuarios_ids)
    filmes_ids_set = set(filmes_ids)

    ratings_df['UserID'] = ratings_df['UserID'].astype(str)
    ratings_df['MovieID'] = ratings_df['MovieID'].astype(str)

    ratings_filtradas = ratings_df[
        ratings_df['UserID'].isin(usuarios_ids_set) &
        ratings_df['MovieID'].isin(filmes_ids_set)
    ]

    if hasattr(config, 'LIMIT_RATINGS') and config.LIMIT_RATINGS:
        ratings_filtradas = ratings_filtradas.head(config.LIMIT_RATINGS)

    print(f"Injecting {len(ratings_filtradas)} ratings aligned with the scope.")

    for row in ratings_filtradas.itertuples(index=False):
        uid = row.UserID
        mid = row.MovieID
        score = row.Rating
        ts = row.Timestamp

        rating_uri = URIRef(f"{config.MOREO_URI}RATING_U{uid}_M{mid}")
        user_uri = URIRef(f"{config.MOREO_URI}USER_{uid}")
        movie_uri = URIRef(f"{config.MOREO_URI}MOVIE_{mid}")

        g.add((rating_uri, RDF.type, config.MOREO.UserRating))
        g.add((user_uri, config.MOREO.performs_rating, rating_uri))
        g.add((rating_uri, config.MOREO.is_about, movie_uri))

        g.add((rating_uri, config.MOREO.has_score, Literal(int(score), datatype=XSD.integer)))

        dt_object = datetime.fromtimestamp(ts)
        iso_timestamp = dt_object.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        g.add((rating_uri, config.MOREO.has_timestamp, Literal(iso_timestamp, datatype=XSD.dateTimeStamp)))

    # Calcula e injeta a média de avaliações (GlobalRating) para cada filme avaliado
    print("Calculating and injecting Global Ratings...")
    avg_ratings = ratings_filtradas.groupby('MovieID')['Rating'].mean()
    for mid, avg_val in avg_ratings.items():
        movie_uri = URIRef(f"{config.MOREO_URI}MOVIE_{mid}")
        global_rating_uri = URIRef(f"{config.MOREO_URI}GLOBAL_RATING_{mid}")

        g.add((global_rating_uri, RDF.type, config.MOREO.GlobalRating))
        g.add((global_rating_uri, config.MOREO.is_global_rating_quality_of, movie_uri))
        g.add((global_rating_uri, config.MOREO.has_average_score, Literal(float(avg_val), datatype=XSD.float)))

def enriquecer_via_wikidata(g, filmes_validos):
    limite = config.LIMIT_MOVIES
    print(f"Batch reconciling countries for the first {limite} movies...")

    movies_df = pd.read_csv(
        config.DATASET_DIR / "movies.dat",
        sep="::", engine="python", encoding="ISO-8859-1",
        names=["MovieID", "Title", "Genres"]
    ).head(limite)

    lista_busca = []
    filmes_info = {}

    for _, row in movies_df.iterrows():
        mid = row["MovieID"]
        title = row["Title"]
        ano_match = re.search(r'\((\d{4})\)', title)
        ano = ano_match.group(1) if ano_match else None

        if ano:
            titulo_base = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
            titulo_base = re.split(r'\s*\(', titulo_base)[0].strip()
            match_artigo = re.match(r'^(.*),\s+(The|A|An|Les|La|Le|Il|El|L\')\s*$', titulo_base, flags=re.IGNORECASE)
            if match_artigo:
                titulo_limpo = f"{match_artigo.group(2)} {match_artigo.group(1)}"
            else:
                titulo_limpo = titulo_base

            lista_busca.append({'titulo': titulo_limpo, 'ano': ano})
            filmes_info[mid] = {'chave': f"{titulo_limpo}_{ano}", 'title_original': title}

    mapa_resultados = wikidata_service.buscar_paises_em_lote(lista_busca)

    for mid, info in filmes_info.items():
        movie_uri = URIRef(f"{config.MOREO_URI}MOVIE_{mid}")
        chave_busca = info['chave']

        if chave_busca in mapa_resultados:
            dados = mapa_resultados[chave_busca]
            country_url = dados["country_url"]
            nome_pais = dados["country_label"]
            country_qid = country_url.split("/")[-1]

            nation_uri = URIRef(f"{config.MOREO_URI}NATION_{country_qid}")
            g.add((nation_uri, RDF.type, config.MOREO.Nation))
            g.add((nation_uri, config.MOREO.has_name, Literal(nome_pais, datatype=XSD.string)))
            g.add((nation_uri, config.OWL.sameAs, URIRef(country_url)))
            g.add((movie_uri, config.MOREO.has_nationality, nation_uri))
            print(f"[SUCCESS] {info['title_original']} -> Country mapped: {nome_pais}")
        else:
            print(f"[WARNING] {info['title_original']} had no countries located in the batch return.")

def enriquecer_diretores_via_wikidata(g, filmes_validos):
    limite = config.LIMIT_MOVIES
    print(f"Batch reconciling directors for the first {limite} movies...")

    movies_df = pd.read_csv(
        config.DATASET_DIR / "movies.dat",
        sep="::", engine="python", encoding="ISO-8859-1",
        names=["MovieID", "Title", "Genres"]
    ).head(limite)

    lista_busca = []
    filmes_info = {}

    for _, row in movies_df.iterrows():
        mid = row["MovieID"]
        title = row["Title"]
        ano_match = re.search(r'\((\d{4})\)', title)
        ano = ano_match.group(1) if ano_match else None

        if ano:
            titulo_base = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
            titulo_base = re.split(r'\s*\(', titulo_base)[0].strip()
            match_artigo = re.match(r'^(.*),\s+(The|A|An|Les|La|Le|Il|El|L\')\s*$', titulo_base, flags=re.IGNORECASE)
            if match_artigo:
                titulo_limpo = f"{match_artigo.group(2)} {match_artigo.group(1)}"
            else:
                titulo_limpo = titulo_base

            lista_busca.append({'titulo': titulo_limpo, 'ano': ano})
            filmes_info[mid] = {'chave': f"{titulo_limpo}_{ano}", 'title_original': title}

    print(f"Sending batch of {len(lista_busca)} movies to fetch directors from Wikidata...")
    mapa_resultados = wikidata_service.buscar_diretores_em_lote(lista_busca)

    for mid, info in filmes_info.items():
        movie_uri = URIRef(f"{config.MOREO_URI}MOVIE_{mid}")
        chave_busca = info['chave']

        if chave_busca in mapa_resultados:
            diretores = mapa_resultados[chave_busca]
            diretores_processados = set()

            for dados in diretores:
                director_url = dados["director_url"]
                director_qid = director_url.split("/")[-1]

                if director_qid in diretores_processados:
                    continue
                diretores_processados.add(director_qid)

                person_uri = URIRef(f"{config.MOREO_URI}PERSON_{director_qid}")
                g.add((person_uri, RDF.type, config.MOREO.Person))
                g.add((person_uri, config.OWL.sameAs, URIRef(director_url)))

                if "director_label" in dados:
                    nome_completo = dados["director_label"]
                    g.add((person_uri, config.MOREO.has_name, Literal(nome_completo, datatype=XSD.string)))

                if "birth_date" in dados:
                    try:
                        data_nascimento_str = dados["birth_date"].split("T")[0]
                        data_nascimento = datetime.strptime(data_nascimento_str, "%Y-%m-%d")
                        hoje = datetime.now()
                        idade = hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
                        g.add((person_uri, config.MOREO.has_age, Literal(idade, datatype=XSD.integer)))
                    except ValueError:
                        pass

                if "country_url" in dados:
                    country_url = dados["country_url"]
                    nome_pais = dados["country_label"]
                    country_qid = country_url.split("/")[-1]

                    nation_uri = URIRef(f"{config.MOREO_URI}NATION_{country_qid}")
                    g.add((nation_uri, RDF.type, config.MOREO.Nation))
                    g.add((nation_uri, config.MOREO.has_name, Literal(nome_pais, datatype=XSD.string)))
                    g.add((nation_uri, config.OWL.sameAs, URIRef(country_url)))
                    g.add((person_uri, config.MOREO.has_nationality, nation_uri))

                role_uri = URIRef(f"{config.MOREO_URI}DIRECTOR_ROLE_{director_qid}_{mid}")
                g.add((role_uri, RDF.type, config.MOREO.DirectorRole))
                g.add((person_uri, config.MOREO.has_role, role_uri))
                g.add((role_uri, config.MOREO.is_played_in, movie_uri))

                nome_print = dados.get('director_label', director_qid)
                print(f"[SUCCESS] {info['title_original']} -> Director mapped: {nome_print}")
        else:
            print(f"[WARNING] {info['title_original']} had no directors located in the batch return.")

def enriquecer_atores_via_wikidata(g, filmes_validos):
    limite = config.LIMIT_MOVIES
    print(f"Batch reconciling actors for the first {limite} movies...")

    movies_df = pd.read_csv(
        config.DATASET_DIR / "movies.dat",
        sep="::", engine="python", encoding="ISO-8859-1",
        names=["MovieID", "Title", "Genres"]
    ).head(limite)

    lista_busca = []
    filmes_info = {}

    for _, row in movies_df.iterrows():
        mid = row["MovieID"]
        title = row["Title"]
        ano_match = re.search(r'\((\d{4})\)', title)
        ano = ano_match.group(1) if ano_match else None

        if ano:
            titulo_base = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
            titulo_base = re.split(r'\s*\(', titulo_base)[0].strip()
            match_artigo = re.match(r'^(.*),\s+(The|A|An|Les|La|Le|Il|El|L\')\s*$', titulo_base, flags=re.IGNORECASE)
            if match_artigo:
                titulo_limpo = f"{match_artigo.group(2)} {match_artigo.group(1)}"
            else:
                titulo_limpo = titulo_base

            lista_busca.append({'titulo': titulo_limpo, 'ano': ano})
            filmes_info[mid] = {'chave': f"{titulo_limpo}_{ano}", 'title_original': title}

    print(f"Sending batch of {len(lista_busca)} movies to fetch actors from Wikidata...")
    mapa_resultados = wikidata_service.buscar_atores_em_lote(lista_busca)

    for mid, info in filmes_info.items():
        movie_uri = URIRef(f"{config.MOREO_URI}MOVIE_{mid}")
        chave_busca = info['chave']

        if chave_busca in mapa_resultados:
            atores = mapa_resultados[chave_busca]
            atores_processados = set()

            for dados in atores:
                actor_url = dados["actor_url"]
                actor_qid = actor_url.split("/")[-1]

                if actor_qid in atores_processados:
                    continue
                atores_processados.add(actor_qid)

                person_uri = URIRef(f"{config.MOREO_URI}PERSON_{actor_qid}")
                g.add((person_uri, RDF.type, config.MOREO.Person))
                g.add((person_uri, config.OWL.sameAs, URIRef(actor_url)))

                if "actor_label" in dados:
                    nome_completo = dados["actor_label"]
                    g.add((person_uri, config.MOREO.has_name, Literal(nome_completo, datatype=XSD.string)))

                if "birth_date" in dados:
                    try:
                        data_nascimento_str = dados["birth_date"].split("T")[0]
                        data_nascimento = datetime.strptime(data_nascimento_str, "%Y-%m-%d")
                        hoje = datetime.now()
                        idade = hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
                        g.add((person_uri, config.MOREO.has_age, Literal(idade, datatype=XSD.integer)))
                    except ValueError:
                        pass

                if "country_url" in dados:
                    country_url = dados["country_url"]
                    nome_pais = dados["country_label"]
                    country_qid = country_url.split("/")[-1]

                    nation_uri = URIRef(f"{config.MOREO_URI}NATION_{country_qid}")
                    g.add((nation_uri, RDF.type, config.MOREO.Nation))
                    g.add((nation_uri, config.MOREO.has_name, Literal(nome_pais, datatype=XSD.string)))
                    g.add((nation_uri, config.OWL.sameAs, URIRef(country_url)))
                    g.add((person_uri, config.MOREO.has_nationality, nation_uri))

                role_uri = URIRef(f"{config.MOREO_URI}ACTOR_ROLE_{actor_qid}_{mid}")
                g.add((role_uri, RDF.type, config.MOREO.ActorRole))
                g.add((person_uri, config.MOREO.has_role, role_uri))
                g.add((role_uri, config.MOREO.is_played_in, movie_uri))

            print(f"[SUCCESS] {info['title_original']} -> {len(atores_processados)} actors mapped")
        else:
            print(f"[WARNING] {info['title_original']} had no actors located in the batch return.")

def enriquecer_premios_filmes_via_wikidata(g, filmes_validos):
    limite = config.LIMIT_MOVIES
    print(f"Batch reconciling movie awards for the first {limite} movies...")

    movies_df = pd.read_csv(
        config.DATASET_DIR / "movies.dat",
        sep="::", engine="python", encoding="ISO-8859-1",
        names=["MovieID", "Title", "Genres"]
    ).head(limite)

    lista_busca = []
    filmes_info = {}

    for _, row in movies_df.iterrows():
        mid = row["MovieID"]
        title = row["Title"]
        ano_match = re.search(r'\((\d{4})\)', title)
        ano = ano_match.group(1) if ano_match else None

        if ano:
            titulo_base = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
            titulo_base = re.split(r'\s*\(', titulo_base)[0].strip()
            match_artigo = re.match(r'^(.*),\s+(The|A|An|Les|La|Le|Il|El|L\')\s*$', titulo_base, flags=re.IGNORECASE)
            if match_artigo:
                titulo_limpo = f"{match_artigo.group(2)} {match_artigo.group(1)}"
            else:
                titulo_limpo = titulo_base

            lista_busca.append({'titulo': titulo_limpo, 'ano': ano})
            filmes_info[mid] = {'chave': f"{titulo_limpo}_{ano}", 'title_original': title}

    mapa_resultados = wikidata_service.buscar_premios_filmes_em_lote(lista_busca)

    for mid, info in filmes_info.items():
        movie_uri = URIRef(f"{config.MOREO_URI}MOVIE_{mid}")
        chave_busca = info['chave']

        if chave_busca in mapa_resultados:
            premios = mapa_resultados[chave_busca]
            premios_consolidados = {}

            # Consolidação para pegar a data mais recente
            for dados in premios:
                award_qid = dados["award_url"].split("/")[-1]
                award_inst_uri = URIRef(f"{config.MOREO_URI}AWARD_{mid}_{award_qid}")

                if award_inst_uri not in premios_consolidados:
                    premios_consolidados[award_inst_uri] = dados
                else:
                    nova_data = dados.get("pointInTime")
                    data_atual = premios_consolidados[award_inst_uri].get("pointInTime")
                    if nova_data and data_atual:
                        if nova_data > data_atual:
                            premios_consolidados[award_inst_uri]["pointInTime"] = nova_data
                    elif nova_data:
                        premios_consolidados[award_inst_uri]["pointInTime"] = nova_data

            # Inserção no Grafo RDF usando os dados consolidados
            for award_inst_uri, dados in premios_consolidados.items():
                status = dados["status"]

                g.add((award_inst_uri, RDF.type, config.MOREO.Award))

                if "awardLabel" in dados:
                    g.add((award_inst_uri, config.MOREO.has_category_name, Literal(dados["awardLabel"], datatype=XSD.string)))

                if "eventLabel" in dados:
                    g.add((award_inst_uri, config.MOREO.has_ceremony_name, Literal(dados["eventLabel"], datatype=XSD.string)))

                if "pointInTime" in dados:
                    raw_date = dados["pointInTime"]
                    if raw_date.startswith("+"):
                        raw_date = raw_date[1:]
                    g.add((award_inst_uri, config.MOREO.has_award_date, Literal(raw_date, datatype=XSD.dateTimeStamp)))

                if status == "won":
                    g.add((movie_uri, config.MOREO.has_award, award_inst_uri))
                    g.add((award_inst_uri, config.MOREO.is_award_of, movie_uri))
                else:
                    g.add((movie_uri, config.MOREO.has_indication, award_inst_uri))

            print(f"[SUCCESS] {info['title_original']} -> {len(premios_consolidados)} movie awards mapped")
        else:
            print(f"[WARNING] {info['title_original']} had no movie awards located in the batch return.")

def enriquecer_premios_pessoas_via_wikidata(g, filmes_validos):
    limite = config.LIMIT_MOVIES
    print(f"Batch reconciling cast and crew awards for the first {limite} movies...")

    movies_df = pd.read_csv(
        config.DATASET_DIR / "movies.dat",
        sep="::", engine="python", encoding="ISO-8859-1",
        names=["MovieID", "Title", "Genres"]
    ).head(limite)

    lista_busca = []
    filmes_info = {}

    for _, row in movies_df.iterrows():
        mid = row["MovieID"]
        title = row["Title"]
        ano_match = re.search(r'\((\d{4})\)', title)
        ano = ano_match.group(1) if ano_match else None

        if ano:
            titulo_base = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
            titulo_base = re.split(r'\s*\(', titulo_base)[0].strip()
            match_artigo = re.match(r'^(.*),\s+(The|A|An|Les|La|Le|Il|El|L\')\s*$', titulo_base, flags=re.IGNORECASE)
            if match_artigo:
                titulo_limpo = f"{match_artigo.group(2)} {match_artigo.group(1)}"
            else:
                titulo_limpo = titulo_base

            lista_busca.append({'titulo': titulo_limpo, 'ano': ano})
            filmes_info[mid] = {'chave': f"{titulo_limpo}_{ano}", 'title_original': title}

    mapa_resultados = wikidata_service.buscar_premios_pessoas_em_lote(lista_busca)

    for mid, info in filmes_info.items():
        chave_busca = info['chave']

        if chave_busca in mapa_resultados:
            premios = mapa_resultados[chave_busca]
            premios_consolidados = {}

            # Consolidação para pegar a data mais recente
            for dados in premios:
                person_qid = dados["person_url"].split("/")[-1]
                award_qid = dados["award_url"].split("/")[-1]

                award_inst_uri = URIRef(f"{config.MOREO_URI}AWARD_ROLE_{person_qid}_{mid}_{award_qid}")

                if award_inst_uri not in premios_consolidados:
                    premios_consolidados[award_inst_uri] = dados
                else:
                    nova_data = dados.get("pointInTime")
                    data_atual = premios_consolidados[award_inst_uri].get("pointInTime")
                    if nova_data and data_atual:
                        if nova_data > data_atual:
                            premios_consolidados[award_inst_uri]["pointInTime"] = nova_data
                    elif nova_data:
                        premios_consolidados[award_inst_uri]["pointInTime"] = nova_data

            # Inserção no Grafo RDF usando os dados consolidados
            for award_inst_uri, dados in premios_consolidados.items():
                person_qid = dados["person_url"].split("/")[-1]
                role_type = dados["personRole"]
                status = dados["status"]

                if role_type == "director":
                    role_uri = URIRef(f"{config.MOREO_URI}DIRECTOR_ROLE_{person_qid}_{mid}")
                else:
                    role_uri = URIRef(f"{config.MOREO_URI}ACTOR_ROLE_{person_qid}_{mid}")

                g.add((award_inst_uri, RDF.type, config.MOREO.Award))

                if "awardLabel" in dados:
                    g.add((award_inst_uri, config.MOREO.has_category_name, Literal(dados["awardLabel"], datatype=XSD.string)))

                if "eventLabel" in dados:
                    g.add((award_inst_uri, config.MOREO.has_ceremony_name, Literal(dados["eventLabel"], datatype=XSD.string)))

                if "pointInTime" in dados:
                    raw_date = dados["pointInTime"]
                    if raw_date.startswith("+"):
                        raw_date = raw_date[1:]
                    g.add((award_inst_uri, config.MOREO.has_award_date, Literal(raw_date, datatype=XSD.dateTimeStamp)))

                if status == "won":
                    g.add((role_uri, config.MOREO.has_award, award_inst_uri))
                    g.add((award_inst_uri, config.MOREO.is_award_of, role_uri))
                else:
                    g.add((role_uri, config.MOREO.has_indication, award_inst_uri))

            print(f"[SUCCESS] {info['title_original']} -> {len(premios_consolidados)} cast/crew awards mapped")
        else:
            print(f"[WARNING] {info['title_original']} had no cast/crew awards located in the batch return.")
