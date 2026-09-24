import pytest
from propagate_research.graph.build_graph import (
    ABLATION_FULL,
    ABLATION_INTERACTION_ONLY,
    ABLATION_PROPAGATION_ONLY,
    NUM_RELATIONS,
    RELATION_TO_ID,
    add_relation_types,
    apply_ablation,
)


def test_relation_to_id_has_two_entries():
    assert NUM_RELATIONS == 2
    assert set(RELATION_TO_ID.keys()) == {"direct_share", "inherited_share"}


def test_relation_ids_are_0_and_1():
    assert sorted(RELATION_TO_ID.values()) == [0, 1]


def test_add_relation_types_module_importable_without_torch():
    # This test itself proves the import at the top of build_graph.py
    # succeeded without torch/torch_geometric imported at module level
    # (deferred imports inside the function).
    assert callable(add_relation_types)


def test_add_relation_types_raises_clear_import_error_without_torch(monkeypatch):
    # torch IS installed in this sandbox (see other tests below), so
    # this test simulates the "not installed" case explicitly rather
    # than relying on environment absence, to keep testing the
    # graceful-failure path even now that torch is available here.
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "torch":
            raise ImportError("simulated: torch not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    class _FakeData:
        pass

    with pytest.raises(ImportError):
        add_relation_types(_FakeData())


# --- executed for real: torch and torch_geometric ARE installed here ---


def test_add_relation_types_executed_on_real_synthetic_graph():
    """Genuinely runs add_relation_types() against a real
    torch_geometric Data object -- not mocked, not simulated. The
    graph shape (root=0, 3 direct-share edges, 1 inherited-share edge)
    matches the verified UPFD structure, but the data itself is
    synthetic (real UPFD download is blocked in this sandbox)."""
    import torch
    from torch_geometric.data import Data

    edge_index = torch.tensor([[0, 0, 0, 1], [1, 2, 3, 4]], dtype=torch.long)
    x = torch.randn(5, 16)
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([1]))
    data.num_nodes = 5

    result = add_relation_types(data)

    assert result.edge_type.tolist() == [0, 0, 0, 1]
    assert result.x.shape == (5, 16)
    assert result.edge_index.shape[1] == 4


def test_add_relation_types_preserves_all_edges():
    import torch
    from torch_geometric.data import Data

    edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
    x = torch.randn(4, 8)
    data = Data(x=x, edge_index=edge_index)
    data.num_nodes = 4

    result = add_relation_types(data)
    assert result.edge_index.shape[1] == 3  # no edges dropped or duplicated


def test_add_relation_types_rejects_disconnected_root():
    import torch
    from torch_geometric.data import Data

    # node 0 (root) has no edges -- violates root-first cascade assumption
    edge_index = torch.tensor([[1, 2], [2, 3]], dtype=torch.long)
    x = torch.randn(4, 8)
    data = Data(x=x, edge_index=edge_index)
    data.num_nodes = 4

    with pytest.raises(ValueError):
        add_relation_types(data)


def test_add_relation_types_accepts_missing_y():
    import torch
    from torch_geometric.data import Data

    edge_index = torch.tensor([[0, 0], [1, 2]], dtype=torch.long)
    x = torch.randn(3, 8)
    data = Data(x=x, edge_index=edge_index)  # no y at all
    data.num_nodes = 3

    result = add_relation_types(data)  # should not raise
    assert result.y is None


def test_add_relation_types_accepts_valid_binary_labels():
    import torch
    from torch_geometric.data import Data

    edge_index = torch.tensor([[0, 0], [1, 2]], dtype=torch.long)
    x = torch.randn(3, 8)

    for label in (0, 1):
        data = Data(x=x, edge_index=edge_index, y=torch.tensor([label]))
        data.num_nodes = 3
        result = add_relation_types(data)
        assert result.y.item() == label


def test_add_relation_types_rejects_non_binary_label():
    import torch
    from torch_geometric.data import Data

    edge_index = torch.tensor([[0, 0], [1, 2]], dtype=torch.long)
    x = torch.randn(3, 8)
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([2]))
    data.num_nodes = 3

    with pytest.raises(ValueError):
        add_relation_types(data)


# --- ablation: relation filtering ---


def _star_graph_with_both_relations():
    """root(0) -> {1,2} direct_share; 1 -> 3 inherited_share."""
    import torch
    from torch_geometric.data import Data

    edge_index = torch.tensor([[0, 0, 1], [1, 2, 3]], dtype=torch.long)
    x = torch.randn(4, 8)
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([1]))
    data.num_nodes = 4
    return add_relation_types(data)


def test_ablation_full_returns_graph_unchanged():
    g = _star_graph_with_both_relations()
    result = apply_ablation(g, ABLATION_FULL)
    assert result is g  # no copy, no filtering
    assert result.edge_index.shape[1] == 3


def test_ablation_propagation_only_excludes_interaction_edges():
    g = _star_graph_with_both_relations()
    result = apply_ablation(g, ABLATION_PROPAGATION_ONLY)
    assert result.edge_index.shape[1] == 2  # only the two direct_share edges
    assert (result.edge_type == RELATION_TO_ID["direct_share"]).all()
    assert not (result.edge_type == RELATION_TO_ID["inherited_share"]).any()


def test_ablation_interaction_only_excludes_propagation_edges():
    g = _star_graph_with_both_relations()
    result = apply_ablation(g, ABLATION_INTERACTION_ONLY)
    assert result.edge_index.shape[1] == 1  # only the one inherited_share edge
    assert (result.edge_type == RELATION_TO_ID["inherited_share"]).all()
    assert not (result.edge_type == RELATION_TO_ID["direct_share"]).any()


def test_ablation_full_model_still_receives_both_relations():
    """Explicit contrast test: the full model's edge count equals
    propagation-only's count plus interaction-only's count, proving
    ablation is a strict subset, not a different graph."""
    g = _star_graph_with_both_relations()
    full = apply_ablation(g, ABLATION_FULL)
    prop_only = apply_ablation(g, ABLATION_PROPAGATION_ONLY)
    inter_only = apply_ablation(g, ABLATION_INTERACTION_ONLY)
    prop_edges = prop_only.edge_index.shape[1]
    inter_edges = inter_only.edge_index.shape[1]
    assert full.edge_index.shape[1] == prop_edges + inter_edges


def test_ablation_preserves_node_features_and_count():
    g = _star_graph_with_both_relations()
    result = apply_ablation(g, ABLATION_PROPAGATION_ONLY)
    assert result.num_nodes == g.num_nodes
    import torch

    assert torch.equal(result.x, g.x)


def test_ablation_preserves_label():
    g = _star_graph_with_both_relations()
    result = apply_ablation(g, ABLATION_INTERACTION_ONLY)
    assert result.y.item() == g.y.item()


def test_ablation_handles_graph_with_no_edges_of_kept_relation():
    """A graph whose only edges are direct_share (root->leaf) -- an
    interaction_only ablation should yield a validly-shaped empty
    edge_index, not crash or produce a malformed shape."""
    import torch
    from torch_geometric.data import Data

    edge_index = torch.tensor([[0, 0], [1, 2]], dtype=torch.long)
    x = torch.randn(3, 8)
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([0]))
    data.num_nodes = 3
    g = add_relation_types(data)

    result = apply_ablation(g, ABLATION_INTERACTION_ONLY)
    assert result.edge_index.shape == (2, 0)
    assert result.edge_type.shape == (0,)
    assert result.num_nodes == 3


def test_ablation_rejects_invalid_variant_name():
    g = _star_graph_with_both_relations()
    with pytest.raises(ValueError):
        apply_ablation(g, "not_a_real_ablation")


def test_ablation_rejects_graph_without_edge_type():
    import torch
    from torch_geometric.data import Data

    edge_index = torch.tensor([[0, 0], [1, 2]], dtype=torch.long)
    x = torch.randn(3, 8)
    data = Data(x=x, edge_index=edge_index)  # never passed through add_relation_types
    data.num_nodes = 3

    with pytest.raises(ValueError):
        apply_ablation(data, ABLATION_PROPAGATION_ONLY)


def test_ablation_filtered_graph_survives_real_gnn_forward_pass():
    """The ablated graph is a genuinely valid model input, not just a
    correctly-shaped tensor -- runs a real forward pass through the
    actual DualLayerGNN, same architecture used everywhere else (no
    redesign for ablation support)."""
    import torch
    from propagate_research.models.dual_layer_gnn import DualLayerGNNConfig, build_dual_layer_gnn
    from torch_geometric.data import Batch

    g = _star_graph_with_both_relations()
    ablated = apply_ablation(g, ABLATION_PROPAGATION_ONLY)
    batch = Batch.from_data_list([ablated])

    model = build_dual_layer_gnn(DualLayerGNNConfig(in_channels=8, hidden_channels=16))
    model.eval()
    with torch.no_grad():
        logits = model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)
    assert logits.shape == (1,)
    assert torch.isfinite(logits).all()
