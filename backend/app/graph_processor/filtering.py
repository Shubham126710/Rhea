"""
Graph Processor -- Phases.md Phase 4, Architecture.md §6.

Server-side filtering/ranking of a full relation-typed graph into a
compact representative subset: node IDs, edge list with relation
type, and a relevance score per node. Deliberately never computes
x/y layout coordinates -- Rules.md §2: "Graph layout never happens
server-side... If a PR adds x/y coordinates to that payload, that's
out of scope for the module." Visual layout is the frontend's job
(Phase 7), not this module's.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphSubset:
    node_ids: list[int]
    edges: list[tuple[int, int, int]]  # (source, target, relation_type_id) -- no coordinates
    node_relevance: dict[int, float]  # 0..1, higher = more relevant to the root
    root_index: int
    truncated: bool  # True if the full graph exceeded max_nodes and was filtered down


def build_graph_subset(graph: Any, *, root_index: int = 0, max_nodes: int = 50) -> GraphSubset:
    """`graph` is a relation-typed PyG Data object (has x, edge_index,
    edge_type). Ranks nodes by their (unweighted) hop distance from
    root_index -- closer nodes are more relevant to the root article,
    the same signal early_detection.py already uses as a structural
    proxy (Phase 3 Finding B) -- and keeps the `max_nodes` most
    relevant. If the graph already has `max_nodes` or fewer nodes,
    nothing is filtered (`truncated=False`).
    """
    num_nodes = graph.num_nodes
    edge_index = graph.edge_index
    edge_type = graph.edge_type

    hop_distance = _bfs_hop_distances(num_nodes, edge_index, root_index)

    if num_nodes <= max_nodes:
        keep = set(range(num_nodes))
        truncated = False
    else:
        ranked = sorted(range(num_nodes), key=lambda n: hop_distance.get(n, float("inf")))
        keep = set(ranked[:max_nodes])
        truncated = True

    max_hop = max((d for d in hop_distance.values() if d != float("inf")), default=1) or 1
    node_relevance = {
        n: 1.0 - (hop_distance.get(n, max_hop) / max_hop) if n in keep else 0.0 for n in keep
    }

    edges: list[tuple[int, int, int]] = []
    src_list = edge_index[0].tolist()
    dst_list = edge_index[1].tolist()
    type_list = edge_type.tolist()
    for src, dst, rel in zip(src_list, dst_list, type_list, strict=True):
        if src in keep and dst in keep:
            edges.append((src, dst, rel))

    return GraphSubset(
        node_ids=sorted(keep),
        edges=edges,
        node_relevance=node_relevance,
        root_index=root_index,
        truncated=truncated,
    )


def _bfs_hop_distances(num_nodes: int, edge_index: Any, root_index: int) -> dict[int, int]:
    from collections import deque

    adjacency: dict[int, list[int]] = {n: [] for n in range(num_nodes)}
    src_list = edge_index[0].tolist()
    dst_list = edge_index[1].tolist()
    for src, dst in zip(src_list, dst_list, strict=True):
        adjacency[src].append(dst)
        adjacency[dst].append(src)  # undirected for reachability/ranking purposes only

    distances = {root_index: 0}
    queue = deque([root_index])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor not in distances:
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)
    return distances
