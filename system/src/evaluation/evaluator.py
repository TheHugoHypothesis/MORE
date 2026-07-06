import math
from typing import List, Dict, Set

class MORE_Evaluator:
    def __init__(self, k: int = 10):
        self.k = k

    def calculate_user_metrics(self, recommended_uris: List[str], ground_truth_uris: Set[str]) -> tuple:
        top_k = recommended_uris[:self.k]
        if not ground_truth_uris:
            return 0.0, 0.0, 0.0, 0.0

        # Precision & Recall
        hits = sum(1 for m in top_k if m in ground_truth_uris)
        precision = hits / self.k
        recall = hits / len(ground_truth_uris)

        # NDCG@k
        dcg = sum(
            1.0 / math.log2(i + 2)
            for i, m in enumerate(top_k)
            if m in ground_truth_uris
        )
        # Ideal DCG: all relevant items ranked first (up to k)
        ideal_hits = min(len(ground_truth_uris), self.k)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
        ndcg = dcg / idcg if idcg > 0 else 0.0

        # HR@k
        hr = 1.0 if hits > 0 else 0.0

        return precision, recall, ndcg, hr

    def evaluate_system(self, all_recommendations: Dict[str, List[str]], test_ground_truth: Dict[str, Set[str]]) -> dict:
        total_precision = 0.0
        total_recall = 0.0
        total_ndcg = 0.0
        total_hr = 0.0
        evaluated_users = 0

        gt_sizes = [
            len(v)
            for v in test_ground_truth.values()
        ]

        print(
            "Avg GT size:",
            sum(gt_sizes)/len(gt_sizes)
        )

        for user_uri, ground_truth in test_ground_truth.items():
            if user_uri in all_recommendations:
                rec_list = all_recommendations[user_uri]
                prec, rec, ndcg, hr = self.calculate_user_metrics(rec_list, ground_truth)
                total_precision += prec
                total_recall += rec
                total_ndcg += ndcg
                total_hr += hr
                evaluated_users += 1

        n = evaluated_users if evaluated_users > 0 else 1
        return {
            f"Precision@{self.k}": total_precision / n,
            f"Recall@{self.k}": total_recall / n,
            f"NDCG@{self.k}": total_ndcg / n,
            f"HR@{self.k}": total_hr / n,
        }
