"""
Early-detection robustness curve (Phases.md Batch M): "fraction-of-
observed-propagation" — how does model performance degrade as less of
the cascade has been observed.

IMPORTANT — this is a STRUCTURAL APPROXIMATION, not a literal
wall-clock curve (Phase 3 plan, Finding B): UPFD's distributed
artifact does not retain per-node timestamps, only the already-
resolved directed tree structure. What edge direction *does* encode
(per the UPFD paper's own construction rule) is an approximate
earlier-to-later diffusion order between directly connected nodes.
This module uses BFS depth/order from the root as the observation-
order proxy: "fraction of the cascade observed" = "fraction of nodes
within the first K BFS layers from the root," which is a defensible,
literature-consistent stand-in when true timestamps aren't available
-- but every artifact this module produces must be labeled as such
wherever it's reported (figures, tables, writeup), never presented as
literal elapsed-time early detection.
"""
from dataclasses import dataclass

import networkx as nx
import numpy as np

from propagate_research.graph.relations import ROOT_NODE_INDEX


@dataclass(frozen=True)
class ObservationSnapshot:
    """A snapshot of "what's been observed" at one point along the
    approximated cascade timeline."""

    fraction_observed: float  # in [0, 1], fraction of nodes included
    node_ids: list[int]  # nodes observed at/before this snapshot (includes root)
    bfs_depth_cutoff: int


def bfs_order_from_root(
    edge_index: list[tuple[int, int]],
    num_nodes: int,
    *,
    root_index: int = ROOT_NODE_INDEX,
) -> list[int]:
    """Returns node indices ordered by BFS distance from the root
    (ties broken by node index for determinism), used as the
    structural proxy for chronological observation order. Raises if
    the graph isn't connected to the root -- an early-detection curve
    over an unreachable node isn't meaningful, and silently dropping
    it would misrepresent "fraction observed"."""
    g = nx.Graph()
    g.add_nodes_from(range(num_nodes))
    g.add_edges_from(edge_index)

    if root_index not in g:
        raise ValueError(f"root_index {root_index} not in graph with {num_nodes} nodes")

    distances = nx.single_source_shortest_path_length(g, root_index)
    unreachable = set(range(num_nodes)) - set(distances.keys())
    if unreachable:
        raise ValueError(
            f"{len(unreachable)} node(s) unreachable from root {root_index}: "
            f"{sorted(unreachable)[:5]}{'...' if len(unreachable) > 5 else ''} "
            f"-- BFS observation order is undefined for a disconnected cascade"
        )

    return sorted(distances.keys(), key=lambda n: (distances[n], n))


def observation_snapshots(
    edge_index: list[tuple[int, int]],
    num_nodes: int,
    *,
    fractions: list[float],
    root_index: int = ROOT_NODE_INDEX,
) -> list[ObservationSnapshot]:
    """For each requested fraction in `fractions` (each in (0, 1]),
    returns the snapshot of the first `fraction * num_nodes` nodes in
    BFS order from the root. The root itself is always included
    (fraction > 0 guarantees at least the root plus whatever else
    fits), matching "the earliest thing observed is the news post
    itself" -- the case at fraction=0 (nothing observed, not even the
    root) isn't meaningful for a content+propagation model that always
    has the article text, so fractions must be > 0."""
    if not fractions:
        raise ValueError("fractions must be non-empty")
    for f in fractions:
        if not (0 < f <= 1):
            raise ValueError(f"each fraction must be in (0, 1], got {f}")

    order = bfs_order_from_root(edge_index, num_nodes, root_index=root_index)

    g = nx.Graph()
    g.add_nodes_from(range(num_nodes))
    g.add_edges_from(edge_index)
    depths = dict(nx.single_source_shortest_path_length(g, root_index))

    snapshots = []
    for f in sorted(fractions):
        cutoff_count = max(1, int(np.ceil(f * num_nodes)))
        observed = order[:cutoff_count]
        max_depth_in_snapshot = max((depths.get(n, 0) for n in observed), default=0)
        snapshots.append(
            ObservationSnapshot(
                fraction_observed=f,
                node_ids=observed,
                bfs_depth_cutoff=max_depth_in_snapshot,
            )
        )
    return snapshots
