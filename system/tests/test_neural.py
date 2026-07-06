import unittest
from unittest.mock import MagicMock
import sys
import os
import rdflib
import torch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.inductive.graph_builder import OntologyGraphBuilder
from src.inductive.model import MORE_RGCN
from src.inductive.loss import BPREngine
from src.inductive.inference import NeuralInferenceEngine

class TestNeuralLayer(unittest.TestCase):
    def test_graph_builder_and_split(self):
        g = rdflib.Graph()
        user_uri = "http://www.semanticweb.org/ontologies/2026/3/MOREO#USER_1"
        
        type_pred = rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        rating_class = rdflib.URIRef("http://www.semanticweb.org/ontologies/2026/3/MOREO#UserRating")
        movie_class = rdflib.URIRef("http://www.semanticweb.org/ontologies/2026/3/MOREO#Movie")
        performs_pred = rdflib.URIRef("http://www.semanticweb.org/ontologies/2026/3/MOREO#performs_rating")
        about_pred = rdflib.URIRef("http://www.semanticweb.org/ontologies/2026/3/MOREO#is_about")
        
        for i in range(10):
            rating_uri = f"http://www.semanticweb.org/ontologies/2026/3/MOREO#Rating_{i}"
            movie_uri = f"http://www.semanticweb.org/ontologies/2026/3/MOREO#Movie_{i}"
            g.add((rdflib.URIRef(rating_uri), type_pred, rating_class))
            g.add((rdflib.URIRef(user_uri), performs_pred, rdflib.URIRef(rating_uri)))
            g.add((rdflib.URIRef(rating_uri), about_pred, rdflib.URIRef(movie_uri)))
            g.add((rdflib.URIRef(movie_uri), type_pred, movie_class))
            
        builder = OntologyGraphBuilder(str(performs_pred))
        builder.fit_mappings(g)
        
        self.assertGreater(builder.num_nodes, 0)
        self.assertGreater(builder.num_relations, 0)
        
        train_graph, val_graph, test_graph, train_pairs, val_gt, test_gt, train_seen = builder.build_split_datasets(g)
        
        self.assertEqual(len(train_pairs), 8)
        self.assertEqual(len(val_gt[user_uri]), 1)
        self.assertEqual(len(test_gt[user_uri]), 1)
        
        movie_indices = builder.get_movie_indices(g)
        self.assertEqual(len(movie_indices), 10)

    def test_rgcn_model(self):
        num_nodes = 10
        num_relations = 3
        model = MORE_RGCN(num_nodes, num_relations, embedding_dim=16)
        edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
        edge_type = torch.tensor([0, 1, 2], dtype=torch.long)
        out = model(edge_index, edge_type)
        self.assertEqual(out.shape, (num_nodes, 16))

    def test_bpr_engine(self):
        num_nodes = 10
        num_relations = 3
        model = MORE_RGCN(num_nodes, num_relations, embedding_dim=16)
        train_pairs = [(0, 1), (1, 2)]
        all_movies = [1, 2, 3, 4]
        bpr = BPREngine(model, train_pairs, all_movies)
        u, pos, neg = bpr.sample_triplets(2)
        self.assertEqual(u.shape, (2,))
        self.assertEqual(pos.shape, (2,))
        self.assertEqual(neg.shape, (2,))
        node_embeddings = torch.randn((num_nodes, 16))
        loss = bpr.compute_bpr_loss(node_embeddings, u, pos, neg)
        self.assertGreater(loss.item(), 0.0)

    def test_inference_engine(self):
        num_nodes = 10
        num_relations = 3
        model = MORE_RGCN(num_nodes, num_relations, embedding_dim=16)
        builder = MagicMock()
        builder.node_to_idx = {"user_1": 0, "movie_1": 1, "movie_2": 2}
        engine = NeuralInferenceEngine(model, builder)
        edge_index = torch.tensor([[0, 1], [1, 2]], dtype=torch.long)
        edge_type = torch.tensor([0, 1], dtype=torch.long)
        preds = engine.get_predictions_for_user("user_1", ["movie_1", "movie_2"], edge_index, edge_type)
        self.assertIn("movie_1", preds)
        self.assertIn("movie_2", preds)
        self.assertTrue(0.0 <= preds["movie_1"] <= 1.0)

if __name__ == "__main__":
    unittest.main()
