"""
Derives the two Decision-2 relation types (direct-share, inherited-share)
from a UPFD graph's edge list, with no framework dependency (no torch,
no torch_geometric) — this is deliberate: the correctness of *which
edge is which relation* is pure graph logic and should be fully
unit-testable without a deep-learning framework installed, since the
framework layer (graph/build_graph.py) is just a thin wrapper that
hands these already-validated edge lists to PyG.

VERIFIED DATASET ASSUMPTION (do not weaken without re-verifying):
Per torch_geometric.datasets.UPFD's own documented semantics and its
official example (`news = x[root]`), each UPFD graph is *root-first
indexed* — the source news item is always local node index 0 within
that graph — and the distributed edge_index is built so that:
  - a user node has an edge to the news node iff that user retweeted
    the root news directly
  - two user nodes have an edge iff one retweeted the root news from
    the other (not from the root directly)
This is exactly what Decision 2 needs: no additional field, no extra
hydration, nothing invented — "touches the root" vs "does not touch
the root" is sufficient to split every edge into direct-share vs
inherited-share. If a future UPFD release changes this indexing
convention, ROOT_NODE_INDEX below and the tests in
research/tests/unit/test_relations.py are exactly what would need
re-verifying — that assumption is centralized here on purpose.
"""
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

ROOT_NODE_INDEX = 0

DIRECT_SHARE = "direct_share"
INHERITED_SHARE = "inherited_share"


@dataclass(frozen=True)
class RelationSplit:
    """Edge lists (each a list of (src, dst) int pairs), split by
    relation type. Preserves original edge direction — callers decide
    whether/how to symmetrize for message passing; this module never
    discards directionality, since it may carry the coarse temporal
    signal noted in the Phase 3 plan's Finding B."""

    direct_share: list[tuple[int, int]]
    inherited_share: list[tuple[int, int]]

    @property
    def all_edges(self) -> list[tuple[int, int]]:
        return self.direct_share + self.inherited_share

    def relation_of(self, edge: tuple[int, int]) -> str:
        if edge in self.direct_share:
            return DIRECT_SHARE
        if edge in self.inherited_share:
            return INHERITED_SHARE
        raise ValueError(f"Edge {edge} is not part of this split")


def split_edges_by_relation(
    edge_index: Iterable[tuple[int, int]],
    *,
    root_index: int = ROOT_NODE_INDEX,
) -> RelationSplit:
    """edge_index: an iterable of (src, dst) integer pairs (as you'd
    get from transposing a PyG edge_index tensor's .tolist(), or —
    deliberately — from plain Python lists/tuples, so this function
    never needs torch to be importable).

    Raises ValueError on an empty edge list or on a malformed pair,
    rather than silently returning an empty split — an empty graph is
    a data problem worth surfacing, not swallowing.
    """
    direct: list[tuple[int, int]] = []
    inherited: list[tuple[int, int]] = []
    saw_any = False

    for edge in edge_index:
        saw_any = True
        if len(edge) != 2:
            raise ValueError(f"Malformed edge (expected a 2-tuple): {edge!r}")
        src, dst = int(edge[0]), int(edge[1])
        if src == root_index or dst == root_index:
            direct.append((src, dst))
        else:
            inherited.append((src, dst))

    if not saw_any:
        raise ValueError("Cannot split an empty edge list — graph has no edges")

    return RelationSplit(direct_share=direct, inherited_share=inherited)


def validate_root_first_convention(
    edge_index: Sequence[tuple[int, int]],
    num_nodes: int,
    *,
    root_index: int = ROOT_NODE_INDEX,
) -> None:
    """Sanity check for the assumption this whole module rests on:
    every graph must actually contain the root index, and — for a
    tree-structured cascade with more than one node — the root should
    appear in at least one edge (an isolated root with unreachable
    users would indicate a data problem, not a valid cascade).

    This is meant to be run once per loaded graph as a guard, so a
    violation is caught at data-loading time rather than silently
    producing a wrong direct/inherited split later.
    """
    if num_nodes <= 0:
        raise ValueError("Graph has no nodes")
    if root_index >= num_nodes:
        raise ValueError(
            f"root_index {root_index} is out of range for a graph with {num_nodes} nodes"
        )
    if num_nodes > 1:
        touches_root = any(root_index in (src, dst) for src, dst in edge_index)
        if not touches_root:
            raise ValueError(
                f"Graph has {num_nodes} nodes but no edge touches the root "
                f"node (index {root_index}) — violates the root-first "
                f"cascade assumption this module depends on"
            )
