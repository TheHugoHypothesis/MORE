import os
import sys
import rdflib
import torch

from .graph_builder import OntologyGraphBuilder
from .model import MORE_RGCN
from .loss import BPREngine
from .inference import NeuralInferenceEngine
from src.evaluation.evaluator import MORE_Evaluator
import pandas as pd
import matplotlib.pyplot as plt
import random

def run_training(data_path: str, ontology_path: str, num_epochs: int = 50, lr: float = 0.01, batch_size: int = 1024, model_save_path: str = "model.pt"):
    device = torch.device(
        "cuda" if torch.cuda.is_available()
        else "cpu"
    )

    print("Using device:", device)
    
    print(f"[Neural Train] Loading interaction dataset from {data_path}...")
    g = rdflib.Graph()
    if data_path.endswith(".ttl"):
        g.parse(data_path, format="ttl")
    else:
        g.parse(data_path, format="xml")
    print(f"[Neural Train] Dataset loaded. Found {len(g)} triples.")

    print("[Neural Train] Mapping ontology entities...")
    builder = OntologyGraphBuilder(rating_predicate_uri="http://www.semanticweb.org/ontologies/2026/3/MOREO#performs_rating")
    builder.fit_mappings(g)
    print(f"[Neural Train] Entity mapping complete. Num nodes: {builder.num_nodes}, Num relations: {builder.num_relations}")

    print("[Neural Train] Generating training, validation, and testing splits...")
    train_data, val_data, test_data, train_pairs, val_gt, test_gt, train_seen = builder.build_split_datasets(g)
    train_edge_index, train_edge_type = train_data
    train_edge_index = train_edge_index.to(device)
    train_edge_type = train_edge_type.to(device)
    print(f"[Neural Train] Data splits complete. Num training pairs: {len(train_pairs)}, Num training users: {len(train_seen)}")

    all_movie_indices = builder.get_movie_indices(g)

    model = MORE_RGCN(num_nodes=builder.num_nodes, num_relations=builder.num_relations).to(device)
    bpr_engine = BPREngine(model, train_pairs, all_movie_indices)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    print(f"[Neural Train] Starting R-GCN training for {num_epochs} epochs...")
    
    metrics_history = []
    inference_engine = NeuralInferenceEngine(model, builder)
    evaluator = MORE_Evaluator(k=20)
    candidate_movies = [builder.idx_to_node[idx] for idx in all_movie_indices]
    
    steps_per_epoch = max(1, len(train_pairs) // batch_size)
    
    for epoch in range(num_epochs):
        model.train()
        epoch_loss = 0.0
        for step in range(steps_per_epoch):
            optimizer.zero_grad()
            node_embeddings = model(train_edge_index, train_edge_type)
            u, pos, neg = bpr_engine.sample_triplets(batch_size=batch_size)
            u = u.to(device)
            pos = pos.to(device)
            neg = neg.to(device)

            if len(u) == 0:
                break
                
            loss = bpr_engine.compute_bpr_loss(node_embeddings, u, pos, neg)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        avg_loss = epoch_loss / steps_per_epoch
        
        # Validation evaluation at end of epoch
        model.eval()
        with torch.no_grad():
            node_embeddings = model(train_edge_index, train_edge_type)
            
            # Approximate Validation Loss
            val_u, val_pos, val_neg = [], [], []
            for u_uri, m_uris in val_gt.items():
                if u_uri not in builder.node_to_idx: continue
                u_idx = builder.node_to_idx[u_uri]
                for m_uri in m_uris:
                    if m_uri not in builder.node_to_idx: continue
                    m_idx = builder.node_to_idx[m_uri]
                    neg_idx = random.choice(all_movie_indices)
                    val_u.append(u_idx)
                    val_pos.append(m_idx)
                    val_neg.append(neg_idx)
            
            val_loss = 0.0
            if val_u:
                val_u_t = torch.tensor(val_u).to(device)
                val_pos_t = torch.tensor(val_pos).to(device)
                val_neg_t = torch.tensor(val_neg).to(device)
                val_loss = bpr_engine.compute_bpr_loss(node_embeddings, val_u_t, val_pos_t, val_neg_t).item()
                
            # Validation Metrics (Precision/Recall/NDCG)
            val_recs = {}
            for u_uri in val_gt.keys():
                user_seen = train_seen.get(u_uri, set())
                filtered_candidates = [m for m in candidate_movies if m not in user_seen]
                scores = inference_engine.get_predictions_for_user(u_uri, filtered_candidates, node_embeddings=node_embeddings)
                ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                val_recs[u_uri] = [x[0] for x in ranked]
                
            val_m = evaluator.evaluate_system(val_recs, val_gt)
            metrics_history.append({
                "epoch": epoch + 1,
                "train_loss": avg_loss,
                "val_loss": val_loss,
                "val_precision": val_m.get("Precision@20", 0.0),
                "val_recall": val_m.get("Recall@20", 0.0),
                "val_ndcg": val_m.get("NDCG@20", 0.0),
                "val_hr": val_m.get("HR@20", 0.0)
            })
            
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"[Neural Train] Epoch {epoch+1:03d}/{num_epochs:03d} | Train Loss: {avg_loss:.4f} | Val Loss: {val_loss:.4f} | Val Prec: {val_m.get('Precision@20',0):.4f} | Val Rec: {val_m.get('Recall@20',0):.4f} | Val HR: {val_m.get('HR@20',0):.4f}")

    # Generate and save plots
    model_dir = os.path.dirname(model_save_path)
    system_dir = os.path.dirname(model_dir) if model_dir else os.getcwd()
    graficos_dir = os.path.join(system_dir, "graficos")
    os.makedirs(graficos_dir, exist_ok=True)
    
    df = pd.DataFrame(metrics_history)
    csv_path = os.path.join(graficos_dir, "training_metrics.csv")
    df.to_csv(csv_path, index=False)
    print(f"[Neural Train] Saved training metrics to {csv_path}")
    
    fig, axes = plt.subplots(2, 1, figsize=(10, 10))
    axes[0].plot(df["epoch"], df["train_loss"], label="Train Loss", marker='o')
    axes[0].plot(df["epoch"], df["val_loss"], label="Val Loss", marker='o')
    axes[0].set_title("BPR Loss per Epoch")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()
    axes[0].grid(True)
    
    axes[1].plot(df["epoch"], df["val_precision"], label="Precision@20", marker='s')
    axes[1].plot(df["epoch"], df["val_recall"], label="Recall@20", marker='s')
    axes[1].plot(df["epoch"], df["val_ndcg"], label="NDCG@20", marker='s')
    axes[1].plot(df["epoch"], df["val_hr"], label="HR@20", marker='s')
    axes[1].set_title("Validation Metrics per Epoch")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Score")
    axes[1].legend()
    axes[1].grid(True)
    
    plot_path = os.path.join(graficos_dir, "training_plot.png")
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()
    print(f"[Neural Train] Saved training plot to {plot_path}")

    model_dir = os.path.dirname(model_save_path)
    if model_dir:
        os.makedirs(model_dir, exist_ok=True)

    print(f"[Neural Train] Saving model checkpoint to {model_save_path}...")
    torch.save({
        "model_state_dict": model.state_dict(),
        "node_to_idx": builder.node_to_idx,
        "idx_to_node": builder.idx_to_node,
        "pred_to_idx": builder.pred_to_idx,
        "num_nodes": builder.num_nodes,
        "num_relations": builder.num_relations,
        "train_graph": train_data,
        "val_graph": val_data,
        "test_graph": test_data,
        "val_ground_truth": dict(val_gt),
        "test_ground_truth": dict(test_gt),
        "all_movie_indices": all_movie_indices,
        "train_seen": train_seen,       # user_uri -> set of movie_uris seen in training
    }, model_save_path)
    print("[Neural Train] R-GCN training pipeline complete.")

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import sys
    data_filename = "moreo_populado_completo.owl"
    if len(sys.argv) > 1:
        data_filename = sys.argv[1]
        
    data_p = os.path.join(project_root, "ontology", data_filename)
    ont_p = os.path.join(project_root, "ontology", "moreo_ontology.ttl")
    model_p = os.path.join(project_root, "models", "model.pt")
    run_training(data_p, ont_p, num_epochs=10, model_save_path=model_p)
