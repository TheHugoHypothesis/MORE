import torch
import torch.nn.functional as F


class NeuralInferenceEngine:
    def __init__(self, model, builder):
        self.model = model
        self.builder = builder

    def get_predictions_for_user(self, user_uri, candidate_movie_uris, edge_index=None, edge_type=None, node_embeddings=None):
        self.model.eval()
        with torch.no_grad():
            if user_uri not in self.builder.node_to_idx:
                return {m: 0.0 for m in candidate_movie_uris}
                
            if node_embeddings is None:
                node_embeddings = self.model(edge_index, edge_type)
            user_idx = self.builder.node_to_idx[user_uri]
            
            valid_movie_uris = []
            movie_indices = []
            results = {}
            
            for m_uri in candidate_movie_uris:
                if m_uri in self.builder.node_to_idx:
                    valid_movie_uris.append(m_uri)
                    movie_indices.append(self.builder.node_to_idx[m_uri])
                else:
                    results[m_uri] = 0.0
                    
            if not movie_indices:
                return results
                
            u_emb = node_embeddings[user_idx]
            m_embs = node_embeddings[movie_indices]

            brute_scores = torch.matmul(m_embs, u_emb)

            min_s = torch.min(brute_scores)
            max_s = torch.max(brute_scores)

            if max_s > min_s:
                normalized_scores = (brute_scores - min_s) / (max_s - min_s)
            else:
                normalized_scores = torch.zeros_like(brute_scores)

            for m_uri, score in zip(valid_movie_uris, normalized_scores):
                results[m_uri] = float(score)
                
            return results
