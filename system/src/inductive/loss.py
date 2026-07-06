import torch
import random
import torch.nn.functional as F

class BPREngine:
    def __init__(self, model, user_ratings_tuples, all_movie_indices):
        self.model = model
        self.train_pairs = user_ratings_tuples
        self.train_pairs_set = set(user_ratings_tuples)
        self.movie_pool = all_movie_indices

    def sample_triplets(self, batch_size):
        users, pos_items, neg_items = [], [], []
        samples = random.sample(self.train_pairs, min(batch_size, len(self.train_pairs)))
        for u, i in samples:
            j = random.choice(self.movie_pool)
            while (u, j) in self.train_pairs_set:
                j = random.choice(self.movie_pool)
            users.append(u)
            pos_items.append(i)
            neg_items.append(j)
        return torch.tensor(users, dtype=torch.long), torch.tensor(pos_items, dtype=torch.long), torch.tensor(neg_items, dtype=torch.long)

    def compute_bpr_loss(self, node_embeddings, users, pos_items, neg_items):
        u_emb = node_embeddings[users]
        pos_emb = node_embeddings[pos_items]
        neg_emb = node_embeddings[neg_items]

        pos_scores = torch.sum(u_emb * pos_emb, dim=1)
        neg_scores = torch.sum(u_emb * neg_emb, dim=1)
        loss = -torch.log(torch.sigmoid(pos_scores - neg_scores) + 1e-10).mean()
        return loss
