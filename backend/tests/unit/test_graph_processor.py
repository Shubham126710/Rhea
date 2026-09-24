"""Phase 4 Graph Processor tests."""
import sys
from pathlib import Path

_RESEARCH_ROOT = Path(__file__).resolve().parents[3] / "research"
if str(_RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(_RESEARCH_ROOT))

from app.graph_processor.filtering import build_graph_subset  # noqa: E402


def _star_graph_with_tail(num_leaves: int):
    """Root (0) directly connected to `num_leaves` leaves; node
    `num_leaves` (the last one) is two hops out via leaf 1."""
    import torch
    from propagate_research.graph.build_graph import add_relation_types
    from torch_geometric.data import Data

    edges_src = [0] * num_leaves + [1]
    edges_dst = list(range(1, num_leaves + 1)) + [num_leaves + 1]
    edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
    num_nodes = num_leaves + 2
    x = torch.randn(num_nodes, 16)
    data = Data(x=x, edge_index=edge_index, y=torch.tensor([1]))
    data.num_nodes = num_nodes
    return add_relation_types(data)


def test_build_graph_subset_keeps_everything_when_under_max_nodes():
    graph = _star_graph_with_tail(num_leaves=3)  # 5 nodes total
    subset = build_graph_subset(graph, max_nodes=50)

    assert subset.truncated is False
    assert len(subset.node_ids) == graph.num_nodes
    assert subset.root_index == 0


def test_build_graph_subset_truncates_and_prefers_closer_nodes():
    graph = _star_graph_with_tail(num_leaves=20)  # 22 nodes, node 21 is 2 hops out
    subset = build_graph_subset(graph, max_nodes=10)

    assert subset.truncated is True
    assert len(subset.node_ids) == 10
    assert 0 in subset.node_ids  # root always kept
    # the 2-hop-away node should be dropped before closer 1-hop leaves
    assert (21 not in subset.node_ids) or all(
        subset.node_relevance[n] <= subset.node_relevance.get(21, 0) for n in subset.node_ids
    )


def test_build_graph_subset_has_no_layout_coordinates():
    """Rules.md §2: graph layout never happens server-side."""
    graph = _star_graph_with_tail(num_leaves=3)
    subset = build_graph_subset(graph)

    assert not hasattr(subset, "x")
    assert not hasattr(subset, "y")
    assert not hasattr(subset, "positions")
    # edges are plain (src, dst, relation_type_id) tuples, not
    # coordinate-bearing structures
    for edge in subset.edges:
        assert len(edge) == 3
        assert all(isinstance(v, int) for v in edge)


def test_build_graph_subset_edges_only_reference_kept_nodes():
    graph = _star_graph_with_tail(num_leaves=20)
    subset = build_graph_subset(graph, max_nodes=10)
    kept = set(subset.node_ids)

    for src, dst, _rel in subset.edges:
        assert src in kept
        assert dst in kept


def test_root_relevance_is_highest():
    graph = _star_graph_with_tail(num_leaves=5)
    subset = build_graph_subset(graph, max_nodes=50)

    assert subset.node_relevance[0] == max(subset.node_relevance.values())
