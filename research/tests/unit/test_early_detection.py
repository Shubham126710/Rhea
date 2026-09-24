import pytest
from propagate_research.evaluate.early_detection import (
    bfs_order_from_root,
    observation_snapshots,
)


def test_bfs_order_root_first():
    edges = [(0, 1), (0, 2), (1, 3)]
    order = bfs_order_from_root(edges, num_nodes=4)
    assert order[0] == 0


def test_bfs_order_respects_depth():
    # 0 -> 1, 2 (depth 1); 1 -> 3 (depth 2)
    edges = [(0, 1), (0, 2), (1, 3)]
    order = bfs_order_from_root(edges, num_nodes=4)
    assert order == [0, 1, 2, 3]


def test_bfs_order_ties_broken_by_node_index():
    edges = [(0, 2), (0, 1)]  # both depth 1
    order = bfs_order_from_root(edges, num_nodes=3)
    assert order == [0, 1, 2]


def test_bfs_order_single_node_graph():
    order = bfs_order_from_root([], num_nodes=1)
    assert order == [0]


def test_bfs_order_disconnected_node_raises():
    edges = [(0, 1)]  # node 2 unreachable
    with pytest.raises(ValueError):
        bfs_order_from_root(edges, num_nodes=3)


def test_bfs_order_root_not_in_graph_raises():
    with pytest.raises(ValueError):
        bfs_order_from_root([(1, 2)], num_nodes=3, root_index=99)


def test_observation_snapshots_full_fraction_includes_all_nodes():
    edges = [(0, 1), (0, 2), (1, 3)]
    snapshots = observation_snapshots(edges, num_nodes=4, fractions=[1.0])
    assert len(snapshots[0].node_ids) == 4
    assert set(snapshots[0].node_ids) == {0, 1, 2, 3}


def test_observation_snapshots_small_fraction_includes_root_at_minimum():
    edges = [(0, 1), (0, 2), (1, 3)]
    snapshots = observation_snapshots(edges, num_nodes=4, fractions=[0.1])
    assert 0 in snapshots[0].node_ids
    assert len(snapshots[0].node_ids) >= 1


def test_observation_snapshots_are_monotonically_increasing():
    edges = [(0, 1), (0, 2), (1, 3), (2, 4)]
    snapshots = observation_snapshots(edges, num_nodes=5, fractions=[0.2, 0.5, 1.0])
    counts = [len(s.node_ids) for s in snapshots]
    assert counts == sorted(counts)


def test_observation_snapshots_bfs_depth_cutoff_reported():
    edges = [(0, 1), (1, 2)]  # chain: depths 0, 1, 2
    snapshots = observation_snapshots(edges, num_nodes=3, fractions=[1.0])
    assert snapshots[0].bfs_depth_cutoff == 2


def test_observation_snapshots_rejects_zero_fraction():
    with pytest.raises(ValueError):
        observation_snapshots([(0, 1)], num_nodes=2, fractions=[0.0])


def test_observation_snapshots_rejects_fraction_above_one():
    with pytest.raises(ValueError):
        observation_snapshots([(0, 1)], num_nodes=2, fractions=[1.5])


def test_observation_snapshots_rejects_empty_fractions_list():
    with pytest.raises(ValueError):
        observation_snapshots([(0, 1)], num_nodes=2, fractions=[])


def test_observation_snapshots_single_node_graph_full_fraction():
    snapshots = observation_snapshots([], num_nodes=1, fractions=[1.0])
    assert snapshots[0].node_ids == [0]
    assert snapshots[0].bfs_depth_cutoff == 0
