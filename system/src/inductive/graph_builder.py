import random
from collections import defaultdict
import rdflib
import torch

class OntologyGraphBuilder:
    def __init__(self, rating_predicate_uri: str):
        self.node_to_idx = {}
        self.pred_to_idx = {}
        self.idx_to_node = {}
        self.rating_pred = rating_predicate_uri
        self.num_nodes = 0
        self.num_relations = 0

    def fit_mappings(self, graph: rdflib.Graph):
        node_set = set()
        pred_set = set()
        for s, p, o in graph:
            if not isinstance(o, rdflib.Literal):
                node_set.add(str(s))
                node_set.add(str(o))
                pred_set.add(str(p))
        self.node_to_idx = {node: idx for idx, node in enumerate(sorted(node_set))}
        self.idx_to_node = {idx: node for node, idx in self.node_to_idx.items()}
        self.pred_to_idx = {pred: idx for idx, pred in enumerate(sorted(pred_set))}
        self.num_nodes = len(self.node_to_idx)
        self.num_relations = len(self.pred_to_idx)

    def to_tensors(self, triples_list):
        edge_list = []
        edge_types = []
        for s, p, o in triples_list:
            edge_list.append([self.node_to_idx[s], self.node_to_idx[o]])
            edge_types.append(self.pred_to_idx[p])
        
        if len(edge_list) == 0:
            edge_index = torch.empty((2, 0), dtype=torch.long)
            edge_type = torch.empty((0,), dtype=torch.long)
        else:
            edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
            edge_type = torch.tensor(edge_types, dtype=torch.long)
        return edge_index, edge_type

    def build_split_datasets(self, graph: rdflib.Graph):
        rating_nodes = set()
        for s, p, o in graph:
            if str(p) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" and str(o) == "http://www.semanticweb.org/ontologies/2026/3/MOREO#UserRating":
                rating_nodes.add(str(s))
        
        rating_to_user = {}
        rating_to_movie = {}
        for s, p, o in graph:
            s_str, p_str, o_str = str(s), str(p), str(o)
            if p_str == "http://www.semanticweb.org/ontologies/2026/3/MOREO#performs_rating" and o_str in rating_nodes:
                rating_to_user[o_str] = s_str
            elif p_str == "http://www.semanticweb.org/ontologies/2026/3/MOREO#is_performed_by" and s_str in rating_nodes:
                rating_to_user[s_str] = o_str
            elif p_str == "http://www.semanticweb.org/ontologies/2026/3/MOREO#is_about" and s_str in rating_nodes:
                rating_to_movie[s_str] = o_str

        user_ratings = defaultdict(list)
        for r in rating_nodes:
            u = rating_to_user.get(r)
            m = rating_to_movie.get(r)
            if u and m:
                user_ratings[u].append((r, m))

        random.seed(42)
        train_rating_nodes = set()
        val_rating_nodes = set()
        test_rating_nodes = set()
        
        val_ground_truth = defaultdict(set)
        test_ground_truth = defaultdict(set)

        for u, r_m_list in user_ratings.items():
            random.shuffle(r_m_list)
            n = len(r_m_list)
            if n >= 3:
                n_train = int(0.8 * n)
                n_val = int(0.1 * n)
                if n_train == n:
                    n_train -= 2
                    n_val = 1
            elif n == 2:
                n_train = 1
                n_val = 0
            else:
                n_train = 1
                n_val = 0

            u_train = r_m_list[:n_train]
            u_val = r_m_list[n_train:n_train + n_val]
            u_test = r_m_list[n_train + n_val:]

            for r, m in u_train:
                train_rating_nodes.add(r)
            for r, m in u_val:
                val_rating_nodes.add(r)
                val_ground_truth[u].add(m)
            for r, m in u_test:
                test_rating_nodes.add(r)
                test_ground_truth[u].add(m)

        structural_triples = []
        train_rating_triples = []
        val_rating_triples = []
        test_rating_triples = []
        all_rating_nodes = train_rating_nodes | val_rating_nodes | test_rating_nodes

        for s, p, o in graph:
            if isinstance(o, rdflib.Literal):
                continue
            s_str, p_str, o_str = str(s), str(p), str(o)
            if s_str in all_rating_nodes or o_str in all_rating_nodes:
                if s_str in train_rating_nodes or o_str in train_rating_nodes:
                    train_rating_triples.append((s_str, p_str, o_str))
                elif s_str in val_rating_nodes or o_str in val_rating_nodes:
                    val_rating_triples.append((s_str, p_str, o_str))
                elif s_str in test_rating_nodes or o_str in test_rating_nodes:
                    test_rating_triples.append((s_str, p_str, o_str))
            else:
                structural_triples.append((s_str, p_str, o_str))

        train_t = structural_triples + train_rating_triples
        val_t = train_t + val_rating_triples
        test_t = val_t + test_rating_triples

        train_pos_pairs = []
        train_seen = defaultdict(set)  # user_uri -> set of movie_uris seen in training

        for r in train_rating_nodes:
            u = rating_to_user.get(r)
            m = rating_to_movie.get(r)
            if u and m:
                train_seen[u].add(m)
                if u in self.node_to_idx and m in self.node_to_idx:
                    train_pos_pairs.append((self.node_to_idx[u], self.node_to_idx[m]))

        train_graph = self.to_tensors(train_t)
        val_graph = self.to_tensors(val_t)
        test_graph = self.to_tensors(test_t)

        return train_graph, val_graph, test_graph, train_pos_pairs, val_ground_truth, test_ground_truth, dict(train_seen)

    def get_movie_indices(self, graph: rdflib.Graph):
        movie_uris = set()
        for s, p, o in graph:
            if str(p) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                if "Movie" in str(o):
                    movie_uris.add(str(s))
        return [self.node_to_idx[m] for m in movie_uris if m in self.node_to_idx]
