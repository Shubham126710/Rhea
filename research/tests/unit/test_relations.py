import pytest
from propagate_research.graph.relations import (
    DIRECT_SHARE,
    INHERITED_SHARE,
    split_edges_by_relation,
    validate_root_first_convention,
)


def test_edges_touching_root_are_direct_share():
    edges = [(0, 1), (0, 2)]
    split = split_edges_by_relation(edges)
    assert split.direct_share == [(0, 1), (0, 2)]
    assert split.inherited_share == []


def test_edges_between_two_non_root_nodes_are_inherited_share():
    edges = [(0, 1), (1, 2), (2, 3)]
    split = split_edges_by_relation(edges)
    assert split.direct_share == [(0, 1)]
    assert split.inherited_share == [(1, 2), (2, 3)]


def test_realistic_small_cascade_tree():
    """A small realistic UPFD-shaped cascade: root=news(0), three users
    retweeted directly (1,2,3), one user (4) retweeted from user 1."""
    edges = [(0, 1), (0, 2), (0, 3), (1, 4)]
    split = split_edges_by_relation(edges)
    assert set(split.direct_share) == {(0, 1), (0, 2), (0, 3)}
    assert set(split.inherited_share) == {(1, 4)}
    assert split.relation_of((0, 1)) == DIRECT_SHARE
    assert split.relation_of((1, 4)) == INHERITED_SHARE


def test_edge_where_root_is_destination_still_direct_share():
    # direction shouldn't matter for relation classification, only incidence
    split = split_edges_by_relation([(5, 0)])
    assert split.direct_share == [(5, 0)]


def test_all_edges_preserves_both_relations():
    edges = [(0, 1), (1, 2)]
    split = split_edges_by_relation(edges)
    assert set(split.all_edges) == {(0, 1), (1, 2)}


def test_custom_root_index_respected():
    edges = [(7, 1), (1, 2)]
    split = split_edges_by_relation(edges, root_index=7)
    assert split.direct_share == [(7, 1)]
    assert split.inherited_share == [(1, 2)]


def test_empty_edge_list_raises():
    with pytest.raises(ValueError):
        split_edges_by_relation([])


def test_malformed_edge_raises():
    with pytest.raises(ValueError):
        split_edges_by_relation([(0, 1, 2)])  # type: ignore[list-item]


def test_relation_of_unknown_edge_raises():
    split = split_edges_by_relation([(0, 1)])
    with pytest.raises(ValueError):
        split.relation_of((9, 9))


def test_validate_root_first_convention_passes_for_valid_cascade():
    edges = [(0, 1), (1, 2)]
    validate_root_first_convention(edges, num_nodes=3)  # should not raise


def test_validate_root_first_convention_single_node_graph_ok():
    # a news item nobody retweeted: valid, no edges required
    validate_root_first_convention([], num_nodes=1)


def test_validate_root_first_convention_rejects_disconnected_root():
    edges = [(1, 2), (2, 3)]  # root (0) never appears
    with pytest.raises(ValueError):
        validate_root_first_convention(edges, num_nodes=4)


def test_validate_root_first_convention_rejects_zero_nodes():
    with pytest.raises(ValueError):
        validate_root_first_convention([], num_nodes=0)


def test_validate_root_first_convention_rejects_out_of_range_root():
    with pytest.raises(ValueError):
        validate_root_first_convention([(0, 1)], num_nodes=2, root_index=5)
