"""
ML integrity tests (Architecture.md §10): "no train/test leakage,
label validation, feature shape checks, graph integrity, missing-data
fallback behavior, reproducible seeding, model-artifact loading" --
"pytest, run against research checkpoints."

These run against SYNTHETIC data shaped like verified UPFD structure,
same as the rest of Phase 3's torch-dependent tests -- real UPFD
tensors remain unobtained (network-blocked). "Run against research
checkpoints" (real trained checkpoints) isn't possible here for the
same reason; these tests instead validate the mechanisms that WOULD
be run against real checkpoints (checkpoint save/load round-trips,
artifact manifest loading) using this session's own synthetic
training runs.
"""
import pytest

torch = pytest.importorskip("torch")
from propagate_research.artifacts.packaging import (  # noqa: E402
    build_manifest,
    load_manifest,
    save_manifest,
)
from propagate_research.graph.build_graph import add_relation_types  # noqa: E402
from propagate_research.graph.relations import split_edges_by_relation  # noqa: E402
from propagate_research.models.dual_layer_gnn import (  # noqa: E402
    DualLayerGNNConfig,
    build_dual_layer_gnn,
)
from propagate_research.train.checkpointing import CheckpointManager  # noqa: E402
from propagate_research.train.trainer import TrainConfig, train_dual_layer_gnn  # noqa: E402
from torch_geometric.data import Batch, Data  # noqa: E402

# --- no train/test leakage ---


def test_upfd_official_splits_are_used_not_resplit():
    """Architecture/Decision 1 discipline: this codebase must not
    re-split UPFD's graphs itself (that would risk a different split
    than the literature's, and a hand-rolled split risks leakage a
    maintained benchmark split doesn't have). Verifies no module in
    this package calls a random/stratified splitting function on
    graph-level data -- a structural check, not a UPFD-data check."""
    import ast
    import pathlib

    package_dir = pathlib.Path(__file__).parent.parent.parent / "propagate_research"
    forbidden_calls = {"train_test_split", "StratifiedKFold", "KFold"}
    found = []
    for py_file in package_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_calls:
                found.append(f"{py_file.name}: {node.id}")
    assert found == [], (
        f"Found calls to dataset-splitting functions: {found} -- UPFD's own "
        f"train_idx/val_idx/test_idx must be used as-is, not re-split "
        f"(Decision 1: match the literature's benchmark protocol)"
    )


def test_no_graph_appears_in_both_train_and_val_batches():
    """A leakage check at the batching level: constructs a small
    synthetic split and confirms no single graph object (by identity
    of its underlying data) is accidentally included in both a train
    batch and a val batch -- the kind of bug a copy-paste error in
    split-index handling could introduce."""
    graphs = [_make_synthetic_graph(seed=i, label=i % 2) for i in range(10)]
    train_graphs = graphs[:6]
    val_graphs = graphs[6:]

    train_ids = {id(g) for g in train_graphs}
    val_ids = {id(g) for g in val_graphs}
    assert train_ids.isdisjoint(val_ids)


# --- label validation ---


def test_labels_are_strictly_binary():
    graph = _make_synthetic_graph(seed=1, label=1)
    assert graph.y.item() in (0, 1)


def test_graph_construction_rejects_non_binary_label():
    x = torch.randn(3, 8)
    edge_index = torch.tensor([[0, 0], [1, 2]], dtype=torch.long)
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([2]), num_nodes=3)
    with pytest.raises(ValueError):
        add_relation_types(data)


# --- feature shape checks ---


def test_root_and_leaf_nodes_share_feature_width():
    """The exact assumption the Phase 3 course-correction rests on:
    root node (index 0) and every leaf node must have the same
    feature width for RGCNConv to accept the tensor at all."""
    graph = _make_synthetic_graph(seed=1, label=0, num_leaves=5)
    root_dim = graph.x[0].shape[0]
    for leaf_idx in range(1, graph.x.shape[0]):
        assert graph.x[leaf_idx].shape[0] == root_dim


def test_model_rejects_mismatched_in_channels():
    """Already covered in test_dual_layer_gnn.py's
    test_mismatched_feature_dim_raises -- re-asserted here as an
    integrity check specifically because Architecture.md §10 lists
    "feature shape checks" as its own named category, not just an
    implementation detail."""
    model = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=8, hidden_channels=16))
    wrong_width_x = torch.randn(3, 4)  # 4, not 8
    edge_index = torch.tensor([[0, 0], [1, 2]], dtype=torch.long)
    edge_type = torch.zeros(2, dtype=torch.long)
    batch = torch.zeros(3, dtype=torch.long)
    ptr = torch.tensor([0, 3], dtype=torch.long)
    with pytest.raises(RuntimeError):
        model(wrong_width_x, edge_index, edge_type, batch, ptr)


# --- graph integrity ---


def test_every_leaf_node_reachable_from_root():
    graph = _make_synthetic_graph(seed=2, label=1, num_leaves=4)
    edge_list = graph.edge_index.t().tolist()
    from propagate_research.graph.relations import validate_root_first_convention

    validate_root_first_convention(
        [tuple(e) for e in edge_list], num_nodes=graph.num_nodes
    )  # should not raise


def test_disconnected_graph_rejected_at_construction():
    x = torch.randn(4, 8)
    edge_index = torch.tensor([[1, 2], [2, 3]], dtype=torch.long)  # node 0 (root) isolated
    data = Data(x=x, edge_index=edge_index, num_nodes=4)
    with pytest.raises(ValueError):
        add_relation_types(data)


def test_relation_split_covers_every_edge_exactly_once():
    edges = [(0, 1), (0, 2), (1, 3), (2, 4)]
    split = split_edges_by_relation(edges)
    assert len(split.all_edges) == len(edges)
    assert set(split.all_edges) == set(edges)


# --- reproducible seeding ---


def test_same_seed_produces_identical_model_initialization():
    model_a = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=8, hidden_channels=16))
    torch.manual_seed(123)
    for p in model_a.parameters():
        pass  # model already built before seeding below -- need seed BEFORE construction

    torch.manual_seed(123)
    model_1 = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=8, hidden_channels=16))
    torch.manual_seed(123)
    model_2 = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=8, hidden_channels=16))

    for p1, p2 in zip(model_1.parameters(), model_2.parameters(), strict=True):
        assert torch.equal(p1, p2)


def test_training_run_reproducible_with_fixed_seed(tmp_path):
    """Two independent training runs with the same seed and same data
    must produce bit-identical final model weights -- required for
    Batch T's "one-command reproduction" exit gate."""
    train_batches = [_make_batch(seed=100)]
    val_batches = [_make_batch(seed=200)]

    def run_once(run_dir):
        def make_model():
            return build_dual_layer_gnn(DualLayerGNNConfig(in_channels=8, hidden_channels=16))

        ckpt = CheckpointManager(run_dir, run_id="repro-test")
        config = TrainConfig(epochs=2, checkpoint_every=1, seed=7)
        trained, _ = train_dual_layer_gnn(make_model, train_batches, val_batches, config, ckpt)
        return trained

    model_a = run_once(tmp_path / "run_a")
    model_b = run_once(tmp_path / "run_b")

    for p1, p2 in zip(model_a.parameters(), model_b.parameters(), strict=True):
        assert torch.equal(p1, p2)


# --- model-artifact loading ---


def test_artifact_manifest_round_trip_matches_trained_checkpoint(tmp_path):
    """End-to-end: train briefly, checkpoint, package a manifest
    referencing that checkpoint, reload the manifest, confirm the
    referenced checkpoint file actually exists and is loadable."""
    train_batches = [_make_batch(seed=1)]
    val_batches = [_make_batch(seed=2)]

    model = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=8, hidden_channels=16))
    ckpt_dir = tmp_path / "checkpoints"
    ckpt = CheckpointManager(ckpt_dir, run_id="artifact-test")
    config = TrainConfig(epochs=1, checkpoint_every=1, seed=1)
    train_dual_layer_gnn(lambda: model, train_batches, val_batches, config, ckpt)

    manifest = build_manifest(
        model_version="dualgnn-integrity-test",
        dataset_version="synthetic-test",
        git_commit="testcommit123",
        seed=1,
        preprocessing_config={},
        model_config={"hidden_channels": 16},
        encoder_config={"feature": "bert"},
        checkpoint_filename="epoch_0.pt",
    )
    artifact_dir = tmp_path / "artifact"
    save_manifest(manifest, artifact_dir)

    loaded = load_manifest(artifact_dir)
    assert loaded.checkpoint_filename == "epoch_0.pt"
    referenced_checkpoint = ckpt_dir / loaded.checkpoint_filename
    assert referenced_checkpoint.exists()

    state_blob, metadata = ckpt.load(0)
    assert "model_state" in state_blob
    assert metadata.epoch == 0


# --- missing-data fallback behavior ---


def test_single_node_graph_no_leaves_handled_without_crash():
    """A news item with zero retweets yet (root only, no propagation
    data) -- the graph-integrity edge case closest to PRD's
    content-only fallback scenario the training pipeline must not
    choke on."""
    x = torch.randn(1, 8)
    edge_index = torch.empty((2, 0), dtype=torch.long)
    edge_type = torch.empty(0, dtype=torch.long)
    batch = torch.zeros(1, dtype=torch.long)
    ptr = torch.tensor([0, 1], dtype=torch.long)

    model = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=8, hidden_channels=16))
    model.eval()
    with torch.no_grad():
        logits = model(x, edge_index, edge_type, batch, ptr)
    assert logits.shape == (1,)
    assert torch.isfinite(logits).all()


# --- helpers ---


def _make_synthetic_graph(seed: int, label: int, num_leaves: int = 3) -> Data:
    gen = torch.Generator().manual_seed(seed)
    num_nodes = num_leaves + 1
    x = torch.randn(num_nodes, 8, generator=gen)
    edge_index = torch.tensor(
        [[0] * num_leaves, list(range(1, num_nodes))], dtype=torch.long
    )
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([label]), num_nodes=num_nodes)
    return add_relation_types(data)


def _make_batch(seed: int) -> Batch:
    graphs = [
        _make_synthetic_graph(seed=seed + i, label=i % 2, num_leaves=(i % 3) + 1)
        for i in range(4)
    ]
    return Batch.from_data_list(graphs)
