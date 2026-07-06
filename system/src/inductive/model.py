import torch
import torch.nn as nn
from torch_geometric.nn import RGCNConv

class MORE_RGCN(nn.Module):
    def __init__(self, num_nodes, num_relations, embedding_dim=64):
        super(MORE_RGCN, self).__init__()
        self.node_embeddings = nn.Embedding(num_nodes, embedding_dim)
        self.conv1 = RGCNConv(embedding_dim, embedding_dim, num_relations)
        self.conv2 = RGCNConv(embedding_dim, embedding_dim, num_relations)
        self.activation = nn.ReLU()
        self.dropout = nn.Dropout(p=0.2)

    def forward(self, edge_index, edge_type):
        x = self.node_embeddings.weight
        x = self.conv1(x, edge_index, edge_type)
        x = self.activation(x)
        x = self.dropout(x)
        x = self.conv2(x, edge_index, edge_type)
        return x
