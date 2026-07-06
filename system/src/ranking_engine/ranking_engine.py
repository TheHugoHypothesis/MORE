import math
from typing import List, Dict

class MORE_RankingEngine:
    def __init__(self, decay_k: float = 0.1):
        """
        :param decay_k: O hiperparâmetro 'k' que controla a velocidade
                        com que o sistema transiciona do Semântico para o Neural.
        """
        self.k = decay_k

    def _calculate_alpha(self, n_u: int) -> float:
        """Calcula o fator de decaimento exponencial alpha(u) = e^(-k * n_u)"""
        return math.exp(-self.k * n_u)

    def compute_final_ranking(
        self,
        candidate_movie_uris: List[str],
        semantic_scores: Dict[str, float],
        neural_scores: Dict[str, float],
        num_interactions: int,
        top_n: int = 10
    ) -> List[tuple]:
        """
        Aplica a equação neuro-simbólica adaptativa e gera a lista ordenada Top-N.

        :param candidate_movie_uris: Lista de URIs dos filmes ainda não vistos (M_cand)
        :param semantic_scores: Dicionário { URI: score_fracionado [0,1] } vindo do Reasoner
        :param neural_scores: Dicionário { URI: score_minmax [0,1] } vindo da R-GCN
        :param num_interactions: Quantidade de avaliações históricas do usuário (n_u)
        :param top_n: Quantidade de recomendações a retornar
        :return: Lista ordenada de tuplas (URI_do_filme, Score_Final)
        """
        # 1. Calcula o peso dinâmico alpha(u) para o usuário atual
        alpha = self._calculate_alpha(num_interactions)

        final_scores = {}

        # 2. Varre todos os filmes candidatos aplicando a fusão linear
        for movie_uri in candidate_movie_uris:
            # Recupera os scores parciais (caso o filme não tenha disparado regras, assume 0.0)
            score_sem = semantic_scores.get(movie_uri, 0.0)
            score_neu = neural_scores.get(movie_uri, 0.0)

            # Execução da equação matemática:
            # Score_Final = alpha * Score_Sem + (1 - alpha) * Score_Neu
            score_final = (alpha * score_sem) + ((1.0 - alpha) * score_neu)

            final_scores[movie_uri] = score_final

        # 3. Simula o operador 'arg max' generalizado: ordena do maior para o menor score
        # sorted_ranking será uma lista de tuplas: [("URI_Filme_A", 0.94), ("URI_Filme_B", 0.81), ...]
        sorted_ranking = sorted(final_scores.items(), key=lambda item: item[1], reverse=True)

        # 4. Retorna apenas os Top-N primeiros elementos
        return sorted_ranking[:top_n]
