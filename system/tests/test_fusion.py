import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ranking_engine.ranking_engine import MORE_RankingEngine

class TestRankingEngine(unittest.TestCase):
    def test_alpha_calculation(self):
        engine = MORE_RankingEngine(decay_k=0.1)
        self.assertAlmostEqual(engine._calculate_alpha(0), 1.0)
        self.assertLess(engine._calculate_alpha(10), 1.0)
        self.assertGreater(engine._calculate_alpha(10), 0.0)

    def test_compute_final_ranking(self):
        engine = MORE_RankingEngine(decay_k=0.1)
        candidates = ["movie_1", "movie_2", "movie_3"]
        semantic_scores = {"movie_1": 1.0, "movie_2": 0.0}
        neural_scores = {"movie_1": 0.2, "movie_2": 0.8, "movie_3": 0.5}
        
        ranking_cold = engine.compute_final_ranking(candidates, semantic_scores, neural_scores, 0, top_n=2)
        self.assertEqual(len(ranking_cold), 2)
        self.assertEqual(ranking_cold[0][0], "movie_1")
        
        ranking_warm = engine.compute_final_ranking(candidates, semantic_scores, neural_scores, 100, top_n=2)
        self.assertEqual(ranking_warm[0][0], "movie_2")

if __name__ == "__main__":
    unittest.main()
