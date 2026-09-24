import pytest

torch = pytest.importorskip("torch")
from propagate_research.graph.build_graph import add_relation_types  # noqa: E402
from propagate_research.models.dual_layer_gnn import (  # noqa: E402
    DualLayerGNNConfig,
    build_dual_layer_gnn,
)
from torch_geometric.data import Batch, Data  # noqa: E402


def _synthetic_graph(num_leaf_nodes: int, in_dim: int, seed: int = 0) -> Data:
    """A single synthetic UPFD-shaped graph: root=0, `num_leaf_nodes`
    leaves, half direct-share (retweeted root) and half inherited-share
    (retweeted from another user), uniform feature width across every
    node including root -- matching the verified UPFD structure."""
    g = torch.Generator().manual_seed(seed)
    num_nodes = num_leaf_nodes + 1
    x = torch.randn(num_nodes, in_dim, generator=g)

    half = max(1, num_leaf_nodes // 2)
    direct_targets = list(range(1, 1 + half))
    inherited_pairs = [
        (direct_targets[i % len(direct_targets)], i + 1 + half)
        for i in range(num_leaf_nodes - half)
    ]
    src = [0] * len(direct_targets) + [p[0] for p in inherited_pairs]
    dst = direct_targets + [p[1] for p in inherited_pairs]
    edge_index = torch.tensor([src, dst], dtype=torch.long)

    data = Data(x=x, edge_index=edge_index, y=torch.tensor([1]))
    data.num_nodes = num_nodes
    return add_relation_types(data)


def test_forward_pass_runs_and_produces_correct_output_shape():
    """Genuinely executed: builds the real model, real synthetic
    batched graphs, runs a real forward pass."""
    in_dim = 32
    graphs = [_synthetic_graph(5, in_dim, seed=i) for i in range(4)]
    batch = Batch.from_data_list(graphs)

    model = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=in_dim, hidden_channels=16))
    model.eval()

    with torch.no_grad():
        logits = model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)

    assert logits.shape == (4,)
    assert torch.isfinite(logits).all()


def test_forward_pass_single_graph_no_leaves():
    """A news item nobody retweeted: root-only graph, no edges. The
    model must not crash on this degenerate-but-valid case."""
    in_dim = 16
    x = torch.randn(1, in_dim)
    data = Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long), y=torch.tensor([0]))
    data.num_nodes = 1
    data.edge_type = torch.empty((0,), dtype=torch.long)
    batch = Batch.from_data_list([data])

    model = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=in_dim, hidden_channels=8))
    model.eval()
    with torch.no_grad():
        logits = model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)
    assert logits.shape == (1,)
    assert torch.isfinite(logits).all()


def test_forward_pass_varying_graph_sizes_in_one_batch():
    in_dim = 24
    graphs = [_synthetic_graph(n, in_dim, seed=n) for n in [1, 3, 10, 2]]
    batch = Batch.from_data_list(graphs)

    model = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=in_dim, hidden_channels=16))
    model.eval()
    with torch.no_grad():
        logits = model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)
    assert logits.shape == (4,)


def test_backward_pass_produces_gradients():
    """Confirms the model is actually trainable (gradients flow) --
    not just a forward-pass shape check. Still synthetic data, still
    not a claim of learning anything meaningful."""
    in_dim = 16
    graphs = [_synthetic_graph(4, in_dim, seed=i) for i in range(3)]
    batch = Batch.from_data_list(graphs)
    labels = torch.tensor([1.0, 0.0, 1.0])

    model = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=in_dim, hidden_channels=8))
    model.train()

    logits = model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)
    loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, labels)
    loss.backward()

    grad_found = any(
        p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum() > 0
        for p in model.parameters()
    )
    assert grad_found


def test_mismatched_feature_dim_raises():
    """If in_channels doesn't match the actual x width, this should
    fail loudly (a real shape-mismatch error from PyG/torch), not
    silently produce wrong output -- confirms the model doesn't
    silently broadcast/truncate a dimension mismatch."""
    in_dim = 16
    graphs = [_synthetic_graph(3, in_dim, seed=0)]
    batch = Batch.from_data_list(graphs)

    wrong_config = DualLayerGNNConfig(in_channels=in_dim + 5, hidden_channels=8)
    model = build_dual_layer_gnn(wrong_config)
    with pytest.raises(RuntimeError):
        model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)


def test_root_node_index_matches_ptr_convention():
    """Directly confirms the ptr[:-1] == root-node-global-index claim
    this model's forward() relies on, against real PyG Batch objects
    -- not re-deriving it, just locking in the behavior this code
    depends on so a future PyG version change would be caught."""
    d1 = Data(x=torch.randn(3, 4), edge_index=torch.tensor([[0, 0], [1, 2]]))
    d1.num_nodes = 3
    d2 = Data(x=torch.randn(2, 4), edge_index=torch.tensor([[0], [1]]))
    d2.num_nodes = 2
    batch = Batch.from_data_list([d1, d2])
    assert batch.ptr[:-1].tolist() == [0, 3]
