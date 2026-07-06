import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.evaluator import MORE_Evaluator

class TestEvaluator(unittest.TestCase):
    def test_calculate_user_metrics(self):
        evaluator = MORE_Evaluator(k=3)
        recommended = ["movie_1", "movie_2", "movie_3", "movie_4"]
        ground_truth = {"movie_2", "movie_3", "movie_5"}
        precision, recall, ndcg, hr = evaluator.calculate_user_metrics(recommended, ground_truth)
        self.assertAlmostEqual(precision, 2/3)
        self.assertAlmostEqual(recall, 2/3)

    def test_evaluate_system(self):
        evaluator = MORE_Evaluator(k=2)
        recommendations = {
            "user_1": ["movie_1", "movie_2"],
            "user_2": ["movie_3", "movie_4"]
        }
        test_gt = {
            "user_1": {"movie_1"},
            "user_2": {"movie_5"}
        }
        metrics = evaluator.evaluate_system(recommendations, test_gt)
        self.assertAlmostEqual(metrics["Precision@2"], 0.25)
        self.assertAlmostEqual(metrics["Recall@2"], 0.50)
        self.assertAlmostEqual(metrics["HR@2"], 0.50)

if __name__ == "__main__":
    unittest.main()
