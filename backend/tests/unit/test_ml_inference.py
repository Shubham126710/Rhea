"""
Phase 4 ML Inference tests.

Genuinely executed: real DualLayerGNN construction, real
CheckpointManager save/load, real artifact manifest round trip, real
forward pass. The GRAPH DATA is synthetic (shaped like the verified
real UPFD structure -- root=0, direct/inherited edges -- but not
downloaded real UPFD, which this sandbox cannot reach). This mirrors
exactly how Phase 3's own model/trainer code was verified before real
UPFD access existed, and is reported as such, not conflated with a
real-data validation.
"""
import sys
from pathlib import Path

import pytest

_RESEARCH_ROOT = Path(__file__).resolve().parents[3] / "research"
if str(_RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(_RESEARCH_ROOT))

from app.ml_inference.inference import run_inference  # noqa: E402
from app.ml_inference.model_loader import load_model_artifact, load_model_artifact_cached  # noqa: E402
from app.ml_inference.schemas import confidence_band_for_score  # noqa: E402


def _synthetic_relation_typed_graph():
    import torch
    from propagate_research.graph.build_graph import add_relation_types
    from torch_geometric.data import Batch, Data

    edge_index = torch.tensor([[0, 0, 0, 1], [1, 2, 3, 4]], dtype=torch.long)
    x = torch.randn(5, 16)
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([1]))
    data.num_nodes = 5
    data = add_relation_types(data)
    return Batch.from_data_list([data])


def _train_and_save_tiny_artifact(tmp_path):
    """Real save, not a hand-built fixture -- builds a real model,
    saves it via the real CheckpointManager, packages a real manifest
    via the real packaging module. Returns (checkpoint_dir,
    manifest_path, model_version, original_state_dict) for comparison.
    """
    import torch
    from propagate_research.artifacts.packaging import build_manifest, save_manifest
    from propagate_research.models.dual_layer_gnn import DualLayerGNNConfig, build_dual_layer_gnn
    from propagate_research.train.checkpointing import CheckpointManager

    model_version = "test-dualgnn-v0"
    config = DualLayerGNNConfig(in_channels=16, hidden_channels=8, num_relations=2, dropout=0.1)
    model = build_dual_layer_gnn(config)
    optimizer = torch.optim.Adam(model.parameters())

    checkpoint_dir = tmp_path / "checkpoints"
    mgr = CheckpointManager(checkpoint_dir=checkpoint_dir, run_id=model_version)
    mgr.save(epoch=0, model=model, optimizer=optimizer, metrics={"train_loss": 0.5})

    manifest = build_manifest(
        model_version=model_version,
        dataset_version="synthetic-test",
        git_commit="0" * 40,
        seed=42,
        preprocessing_config={"feature": "bert"},
        model_config={"in_channels": 16, "hidden_channels": 8, "num_relations": 2, "dropout": 0.1},
        encoder_config={"type": "upfd_native", "feature": "bert"},
    )
    manifest_path = save_manifest(manifest, tmp_path / "manifest_dir")

    original_state = {k: v.clone() for k, v in model.state_dict().items()}
    return checkpoint_dir, manifest_path, model_version, original_state


def test_load_model_artifact_reconstructs_real_weights(tmp_path):
    checkpoint_dir, manifest_path, model_version, original_state = _train_and_save_tiny_artifact(
        tmp_path
    )

    loaded = load_model_artifact(
        checkpoint_dir=checkpoint_dir, manifest_path=manifest_path, model_version=model_version
    )

    assert loaded.model_version == model_version
    assert loaded.in_channels == 16
    for key, original_tensor in original_state.items():
        loaded_tensor = loaded.model.state_dict()[key]
        assert (original_tensor == loaded_tensor).all().item()


def test_load_model_artifact_rejects_mismatched_version(tmp_path):
    checkpoint_dir, manifest_path, _model_version, _ = _train_and_save_tiny_artifact(tmp_path)

    with pytest.raises(ValueError, match="does not match"):
        load_model_artifact(
            checkpoint_dir=checkpoint_dir,
            manifest_path=manifest_path,
            model_version="some-other-version",
        )


def test_run_inference_produces_correctly_shaped_prediction(tmp_path):
    checkpoint_dir, manifest_path, model_version, _ = _train_and_save_tiny_artifact(tmp_path)
    loaded = load_model_artifact(
        checkpoint_dir=checkpoint_dir, manifest_path=manifest_path, model_version=model_version
    )
    graph = _synthetic_relation_typed_graph()

    result = run_inference(graph, loaded)

    assert result.verdict in ("fake", "real")
    assert 0.0 <= result.raw_score <= 1.0
    assert result.confidence_band in ("low", "moderate", "high")
    assert result.is_calibrated_prob is False
    assert result.model_version == model_version
    assert result.attribution.node_scores == {}
    assert result.attribution.edge_scores == {}
    # synthetic graph has both direct-share (root's edges) and
    # inherited-share (edge 1->4) relations present
    assert result.propagation_available is True
    assert result.interaction_available is True


def test_run_inference_reports_no_interaction_when_graph_has_none(tmp_path):
    """PRD §4.3 content-only fallback: honestly reports False, not a
    fabricated True, when the graph genuinely has no interaction
    edges."""
    import torch
    from propagate_research.graph.build_graph import add_relation_types
    from torch_geometric.data import Batch, Data

    checkpoint_dir, manifest_path, model_version, _ = _train_and_save_tiny_artifact(tmp_path)
    loaded = load_model_artifact(
        checkpoint_dir=checkpoint_dir, manifest_path=manifest_path, model_version=model_version
    )

    # star graph: every edge touches root -- direct-share only, no
    # inherited-share edges at all
    edge_index = torch.tensor([[0, 0, 0], [1, 2, 3]], dtype=torch.long)
    x = torch.randn(4, 16)
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([0]))
    data.num_nodes = 4
    data = add_relation_types(data)
    graph = Batch.from_data_list([data])

    result = run_inference(graph, loaded)

    assert result.propagation_available is True
    assert result.interaction_available is False


@pytest.mark.parametrize(
    "score,expected_band",
    [
        (0.5, "low"),
        (0.05, "high"),  # low P(Fake) = high confidence it's Real
        (0.95, "high"),  # high P(Fake) = high confidence it's Fake
        (0.65, "moderate"),
        (0.35, "moderate"),
        # exact boundaries, both predicted classes
        (0.80, "high"),  # predicted fake, exactly at high threshold
        (0.20, "high"),  # predicted real, exactly at high threshold
        (0.799, "moderate"),  # predicted fake, just below high
        (0.201, "moderate"),  # predicted real, just below high
        (0.60, "moderate"),  # predicted fake, exactly at moderate threshold
        (0.40, "moderate"),  # predicted real, exactly at moderate threshold
        (0.599, "low"),  # predicted fake, just below moderate
        (0.401, "low"),  # predicted real, just below moderate
        (0.0, "high"),  # certain real
        (1.0, "high"),  # certain fake
    ],
)
def test_confidence_band_reflects_predicted_class_confidence(score, expected_band):
    assert confidence_band_for_score(score) == expected_band


def test_confidence_band_rejects_out_of_range_score():
    with pytest.raises(ValueError):
        confidence_band_for_score(1.5)


def test_load_model_artifact_cached_returns_same_object_on_repeat_call(tmp_path):
    """The performance fix: a second call with identical arguments must
    not re-read the checkpoint from disk -- verified here by identity
    (`is`), not just equality, since a fresh load would also pass an
    equality check but still have re-done the disk I/O."""
    checkpoint_dir, manifest_path, model_version, _ = _train_and_save_tiny_artifact(tmp_path)

    first = load_model_artifact_cached(
        checkpoint_dir=checkpoint_dir, manifest_path=manifest_path, model_version=model_version
    )
    second = load_model_artifact_cached(
        checkpoint_dir=checkpoint_dir, manifest_path=manifest_path, model_version=model_version
    )
    assert first is second


def test_load_model_artifact_cached_is_version_safe(tmp_path):
    """Two distinct model_versions (or checkpoint dirs) must never
    collide on one cache entry -- each real artifact loads and stays
    distinct, so a request for version B can never silently receive
    version A's cached model."""
    dir_a, manifest_a, version_a, state_a = _train_and_save_tiny_artifact(tmp_path / "a")
    dir_b, manifest_b, version_b, state_b = _train_and_save_tiny_artifact(tmp_path / "b")
    assert version_a != version_b  # sanity: fixture uses a fixed version string per call

    loaded_a = load_model_artifact_cached(
        checkpoint_dir=dir_a, manifest_path=manifest_a, model_version=version_a
    )
    loaded_b = load_model_artifact_cached(
        checkpoint_dir=dir_b, manifest_path=manifest_b, model_version=version_b
    )

    assert loaded_a is not loaded_b
    assert loaded_a.model_version == version_a
    assert loaded_b.model_version == version_b
    for key, tensor_a in state_a.items():
        assert (loaded_a.model.state_dict()[key] == tensor_a).all().item()
    for key, tensor_b in state_b.items():
        assert (loaded_b.model.state_dict()[key] == tensor_b).all().item()


def test_load_model_artifact_cached_normalizes_str_and_path_to_one_entry(tmp_path):
    """A Path-typed call and an equivalent str-typed call (the shape
    app.core.config.Settings actually passes in production) must share
    one cache entry, not silently create two."""
    checkpoint_dir, manifest_path, model_version, _ = _train_and_save_tiny_artifact(tmp_path)

    via_path = load_model_artifact_cached(
        checkpoint_dir=checkpoint_dir, manifest_path=manifest_path, model_version=model_version
    )
    via_str = load_model_artifact_cached(
        checkpoint_dir=str(checkpoint_dir), manifest_path=str(manifest_path), model_version=model_version
    )
    assert via_path is via_str
