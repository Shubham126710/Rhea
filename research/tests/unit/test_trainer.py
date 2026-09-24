import pytest

torch = pytest.importorskip("torch")
from propagate_research.models.dual_layer_gnn import (  # noqa: E402
    DualLayerGNNConfig,
    build_dual_layer_gnn,
)
from propagate_research.train.checkpointing import CheckpointManager  # noqa: E402
from propagate_research.train.trainer import TrainConfig, train_dual_layer_gnn  # noqa: E402
from torch_geometric.data import Batch, Data  # noqa: E402

IN_CHANNELS = 8


def _make_graph(num_leaf_nodes: int, label: int, seed: int) -> Data:
    """A tiny star-shaped cascade: root (node 0) + num_leaf_nodes users,
    all direct-share edges (root->leaf) for simplicity -- sufficient to
    exercise the model's real forward/backward pass; relation-type
    correctness itself is covered separately in
    tests/unit/test_build_graph.py and test_relations.py."""
    gen = torch.Generator().manual_seed(seed)
    num_nodes = num_leaf_nodes + 1
    x = torch.randn(num_nodes, IN_CHANNELS, generator=gen)
    src = [0] * num_leaf_nodes
    dst = list(range(1, num_nodes))
    edge_index = torch.tensor([src, dst], dtype=torch.long)
    edge_type = torch.zeros(num_leaf_nodes, dtype=torch.long)  # all direct_share
    return Data(x=x, edge_index=edge_index, edge_type=edge_type, y=torch.tensor([label]))


def _make_batches(n_graphs: int, batch_size: int, seed_offset: int = 0) -> list[Batch]:
    graphs = [
        _make_graph(num_leaf_nodes=(i % 4) + 1, label=i % 2, seed=seed_offset + i)
        for i in range(n_graphs)
    ]
    batches = []
    for i in range(0, len(graphs), batch_size):
        batches.append(Batch.from_data_list(graphs[i : i + batch_size]))
    return batches


def test_train_runs_for_real_and_produces_history(tmp_path):
    def make_model():
        return build_dual_layer_gnn(DualLayerGNNConfig(in_channels=IN_CHANNELS, hidden_channels=16))
    train_batches = _make_batches(n_graphs=12, batch_size=4, seed_offset=0)
    val_batches = _make_batches(n_graphs=6, batch_size=3, seed_offset=100)

    ckpt = CheckpointManager(tmp_path, run_id="test-run")
    config = TrainConfig(epochs=2, lr=0.01, checkpoint_every=1, seed=42)

    trained_model, history = train_dual_layer_gnn(
        make_model, train_batches, val_batches, config, ckpt
    )

    assert len(history) == 2
    for epoch_metrics in history:
        assert "train_loss" in epoch_metrics
        assert "val_loss" in epoch_metrics
        assert "val_accuracy" in epoch_metrics
        assert epoch_metrics["train_loss"] == epoch_metrics["train_loss"]  # not NaN


def test_train_writes_checkpoints_at_configured_interval(tmp_path):
    def make_model():
        return build_dual_layer_gnn(DualLayerGNNConfig(in_channels=IN_CHANNELS, hidden_channels=16))
    train_batches = _make_batches(n_graphs=8, batch_size=4)
    val_batches = _make_batches(n_graphs=4, batch_size=4, seed_offset=200)

    ckpt = CheckpointManager(tmp_path, run_id="test-run")
    config = TrainConfig(epochs=3, checkpoint_every=1, seed=1)

    train_dual_layer_gnn(make_model, train_batches, val_batches, config, ckpt)

    assert ckpt.latest_epoch() == 2  # 0-indexed, 3 epochs -> last is epoch 2
    assert (tmp_path / "epoch_0.pt").exists()
    assert (tmp_path / "epoch_1.pt").exists()
    assert (tmp_path / "epoch_2.pt").exists()


def test_train_checkpoint_every_skips_intermediate_epochs(tmp_path):
    def make_model():
        return build_dual_layer_gnn(DualLayerGNNConfig(in_channels=IN_CHANNELS, hidden_channels=16))
    train_batches = _make_batches(n_graphs=8, batch_size=4)
    val_batches = _make_batches(n_graphs=4, batch_size=4, seed_offset=200)

    ckpt = CheckpointManager(tmp_path, run_id="test-run")
    config = TrainConfig(epochs=4, checkpoint_every=2, seed=1)

    train_dual_layer_gnn(make_model, train_batches, val_batches, config, ckpt)

    assert not (tmp_path / "epoch_0.pt").exists()
    assert (tmp_path / "epoch_1.pt").exists()
    assert not (tmp_path / "epoch_2.pt").exists()
    assert (tmp_path / "epoch_3.pt").exists()


def test_train_resumes_from_checkpoint_and_continues_epoch_count(tmp_path):
    """Simulates a Decision-4 disconnect: train 2 epochs, "restart" with
    a fresh model_factory call against the same checkpoint dir, confirm
    it resumes from epoch 2 rather than epoch 0."""
    def make_model():
        return build_dual_layer_gnn(DualLayerGNNConfig(in_channels=IN_CHANNELS, hidden_channels=16))

    train_batches = _make_batches(n_graphs=8, batch_size=4)
    val_batches = _make_batches(n_graphs=4, batch_size=4, seed_offset=200)
    ckpt = CheckpointManager(tmp_path, run_id="resumable-run")

    config = TrainConfig(epochs=2, checkpoint_every=1, seed=1)
    train_dual_layer_gnn(make_model, train_batches, val_batches, config, ckpt)
    assert ckpt.latest_epoch() == 1

    # "Disconnect": fresh model_factory call, same checkpoint manager, more epochs
    config_extended = TrainConfig(epochs=4, checkpoint_every=1, seed=1)
    _, history = train_dual_layer_gnn(make_model, train_batches, val_batches, config_extended, ckpt)

    # only epochs 2 and 3 should have actually been trained this call
    assert [h["epoch"] for h in history] == [2, 3]
    assert ckpt.latest_epoch() == 3


def test_train_device_agnostic_defaults_to_cpu(tmp_path):
    """Confirms no CPU-only assumption is hardcoded -- device is a
    parameter, defaulting to CPU only when not passed. CUDA execution
    itself is untested (no GPU in this sandbox)."""
    import inspect

    from propagate_research.train.trainer import train_dual_layer_gnn as fn

    sig = inspect.signature(fn)
    assert "device" in sig.parameters
    # resolved to cpu inside train_dual_layer_gnn, not hardcoded in the signature
    assert sig.parameters["device"].default is None
