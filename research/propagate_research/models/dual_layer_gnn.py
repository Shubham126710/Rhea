"""
Dual-layer GNN (Architecture.md's Content Encoder -> Propagation GNN +
Interaction GNN -> Fusion -> Classification Head, operationalized per
Decision 2: two relation types within one graph, not two graphs).

STATUS: torch and torch_geometric ARE installed and importable in this
sandbox (confirmed by direct execution). The forward pass below has
been RUN FOR REAL against synthetic batched graphs matching the
verified UPFD structure (root-first indexing, direct/inherited edges,
uniform node-feature width) -- see
tests/unit/test_dual_layer_gnn.py. What has NOT been verified: real
UPFD tensors (download blocked), a real training loop with real
gradient updates converging on real data, and GPU execution (this
sandbox has no CUDA). "Genuinely executes and produces correctly-
shaped output on synthetic data" is a real, meaningful check (it
catches wiring bugs, shape mismatches, and dtype errors) -- it is NOT
the same as "produces a correct or useful classifier," which requires
real data and real training, neither available here.

DESIGN: two RGCNConv layers (num_relations=2: direct_share=0,
inherited_share=1 -- graph/build_graph.py's edge_type convention).
RGCNConv gives each relation type its own weight matrix, which is
exactly the "Propagation GNN" / "Interaction GNN" split Decision 2
calls for, expressed as one model rather than two parallel ones.

Fusion: root-node embedding concatenated with a mean-pooled embedding
over all nodes in each graph, before the classification head. This
follows an established pattern in this exact literature (BiGCN
explicitly reinforces the root/source node's own representation
rather than relying on pooling alone) rather than being invented here
-- pooling alone risks diluting the article's own signal in graphs
with many retweeting users.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DualLayerGNNConfig:
    in_channels: int
    hidden_channels: int = 128
    num_relations: int = 2
    dropout: float = 0.3


def build_dual_layer_gnn(config: DualLayerGNNConfig):
    """Returns a torch.nn.Module. Deferred import (see module
    docstring) so this file stays importable for structural/type
    review even without torch installed, though torch IS available
    in this sandbox as of this session."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch_geometric.nn import RGCNConv, global_mean_pool

    class DualLayerGNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = RGCNConv(config.in_channels, config.hidden_channels, config.num_relations)
            self.conv2 = RGCNConv(
                config.hidden_channels, config.hidden_channels, config.num_relations
            )
            self.dropout = nn.Dropout(config.dropout)
            self.classifier = nn.Sequential(
                nn.Linear(config.hidden_channels * 2, config.hidden_channels),
                nn.ReLU(),
                nn.Dropout(config.dropout),
                nn.Linear(config.hidden_channels, 1),
            )

        def forward(
            self,
            x: "torch.Tensor",
            edge_index: "torch.Tensor",
            edge_type: "torch.Tensor",
            batch: "torch.Tensor",
            ptr: "torch.Tensor",
        ) -> "torch.Tensor":
            """x: [N, in_channels]; edge_index: [2, E]; edge_type: [E];
            batch: [N] graph-membership vector; ptr: [num_graphs + 1]
            cumulative offsets (a PyG Batch's own `.ptr` attribute --
            ptr[:-1] gives each graph's root-node global index, since
            root is always local index 0 within each graph -- verified
            directly against real PyG Batch behavior, see the Phase 3
            report). Returns raw logits, shape [num_graphs] (apply
            sigmoid for P(Fake))."""
            h = F.relu(self.conv1(x, edge_index, edge_type))
            h = self.dropout(h)
            h = self.conv2(h, edge_index, edge_type)

            pooled = global_mean_pool(h, batch)
            root_indices = ptr[:-1]
            root_embed = h[root_indices]

            fused = torch.cat([root_embed, pooled], dim=-1)
            logits = self.classifier(fused).squeeze(-1)
            return logits

    return DualLayerGNN()
