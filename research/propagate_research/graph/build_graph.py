"""
Builds a relation-typed PyG graph from a raw UPFD `Data` object
(x, edge_index, num_nodes), for input to an RGCNConv-style model
(models/dual_layer_gnn.py).

STATUS: torch and torch_geometric ARE installed and importable in
this sandbox (confirmed by direct execution). add_relation_types() has
been RUN FOR REAL against synthetic torch_geometric Data objects
matching the verified UPFD structure (root-first indexing, direct vs
inherited edges) -- see tests/unit/test_build_graph.py's
test_add_relation_types_* tests below. What remains unverified: real
UPFD tensors themselves (dataset download blocked -- Google Drive not
in this sandbox's network allowlist), so the *shape and content* of
real UPFD's x/edge_index have not been inspected, only synthesized to
match documented structure. The relation-splitting LOGIC this wraps
(graph/relations.py) is independently fully tested on its own.

VERIFIED ASSUMPTIONS (see data/upfd_loader.py and the Phase 3 report):
  - root-first indexing (root = local node 0 per graph)
  - edge_index alone determines relation type (direct_share vs
    inherited_share), no extra field needed
  - x has uniform width across all nodes including root, for a given
    UPFD feature type -- inferred from loader structure, not from
    inspecting real tensor values
GRAPH DIRECTION: this module does NOT symmetrize edges (no
ToUndirected()) -- it preserves UPFD's original directed edge_index
exactly, since direction may carry the coarse temporal signal noted
in Finding B (Phase 3 plan). RGCNConv is directional by construction
(it uses edge_type-specific weight matrices per direction), so this is
compatible with, not contrary to, the model architecture below.
"""
from typing import Any

from propagate_research.graph.relations import (
    DIRECT_SHARE,
    INHERITED_SHARE,
    ROOT_NODE_INDEX,
    split_edges_by_relation,
    validate_root_first_convention,
)

RELATION_TO_ID = {DIRECT_SHARE: 0, INHERITED_SHARE: 1}
NUM_RELATIONS = len(RELATION_TO_ID)


def add_relation_types(data: Any, *, root_index: int = ROOT_NODE_INDEX) -> Any:
    """`data`: a torch_geometric.data.Data object with .x, .edge_index
    (shape [2, E]), and .num_nodes set. Returns a NEW Data object
    (does not mutate the input) with:
      - .edge_index rebuilt (same edges, reordered: all direct_share
        edges first, then all inherited_share edges)
      - .edge_type added: a LongTensor of shape [E], aligned with the
        reordered edge_index, valued 0 (direct_share) or 1
        (inherited_share) -- the standard PyG RGCNConv input format

    Raises (via validate_root_first_convention) if the graph doesn't
    actually satisfy the root-first cascade assumption this whole
    pipeline depends on -- a guard against a malformed or unexpected
    graph silently producing a wrong relation split.
    """
    import torch
    from torch_geometric.data import Data

    edge_list = data.edge_index.t().tolist()  # [[src, dst], ...] -> [(src, dst), ...]
    edge_list = [tuple(e) for e in edge_list]

    validate_root_first_convention(edge_list, num_nodes=data.num_nodes, root_index=root_index)
    split = split_edges_by_relation(edge_list, root_index=root_index)

    y = getattr(data, "y", None)
    if y is not None:
        y_value = int(y.item()) if y.numel() == 1 else None
        if y_value is None or y_value not in (0, 1):
            raise ValueError(
                f"Graph label y must be 0 or 1 (Fake/Real, Decision 1's binary "
                f"labeling), got {y.tolist() if hasattr(y, 'tolist') else y!r}"
            )

    ordered_edges = split.direct_share + split.inherited_share
    edge_types = [RELATION_TO_ID[DIRECT_SHARE]] * len(split.direct_share) + [
        RELATION_TO_ID[INHERITED_SHARE]
    ] * len(split.inherited_share)

    new_edge_index = torch.tensor(ordered_edges, dtype=torch.long).t().contiguous()
    new_edge_type = torch.tensor(edge_types, dtype=torch.long)

    new_data = Data(x=data.x, edge_index=new_edge_index, y=getattr(data, "y", None))
    new_data.edge_type = new_edge_type
    new_data.num_nodes = data.num_nodes
    return new_data


# --- ablation support: relation-variant filtering ---
#
# Phases.md's ablation study (LR/RF/MLP/Content+Propagation/
# Content+Interaction/Full model) requires isolating each relation's
# contribution. Per the model's own docstring above, direct_share =
# "Propagation", inherited_share = "Interaction" -- already
# established, not re-decided here.
#
# Mechanism: filters edges (and their edge_type entries) out of an
# already-add_relation_types()'d graph, keeping only the requested
# relation. This does NOT change the model architecture (RGCNConv is
# still built with num_relations=2 every time -- see
# models/dual_layer_gnn.py) -- it changes what the model's INPUT
# contains. A relation with zero edges contributes zero messages
# during message passing, which is a real ablation of that relation's
# effect, not a cosmetic relabeling. Root node and node features are
# never touched; only edges are pruned.

ABLATION_FULL = "full"
ABLATION_PROPAGATION_ONLY = "propagation_only"
ABLATION_INTERACTION_ONLY = "interaction_only"
VALID_ABLATIONS = (ABLATION_FULL, ABLATION_PROPAGATION_ONLY, ABLATION_INTERACTION_ONLY)

_ABLATION_TO_KEPT_RELATION_ID = {
    ABLATION_PROPAGATION_ONLY: RELATION_TO_ID[DIRECT_SHARE],
    ABLATION_INTERACTION_ONLY: RELATION_TO_ID[INHERITED_SHARE],
}


def apply_ablation(data: Any, ablation: str) -> Any:
    """`data`: a Data object already processed by add_relation_types()
    (must have .edge_type set). `ablation`: one of VALID_ABLATIONS.

    ABLATION_FULL returns `data` unchanged (both relations present --
    this is the ordinary dual-layer model, not an ablation).
    ABLATION_PROPAGATION_ONLY / ABLATION_INTERACTION_ONLY return a NEW
    Data object with only the named relation's edges retained; the
    other relation's edges (and their edge_type entries) are removed
    entirely, not merely down-weighted.

    Raises ValueError for an unrecognized ablation string, and if
    `data` has no .edge_type (i.e. wasn't run through
    add_relation_types() first) -- an ablation is only meaningful on
    an already relation-typed graph.
    """
    import torch
    from torch_geometric.data import Data

    if ablation not in VALID_ABLATIONS:
        raise ValueError(f"ablation must be one of {VALID_ABLATIONS}, got {ablation!r}")
    if ablation == ABLATION_FULL:
        return data
    if not hasattr(data, "edge_type") or data.edge_type is None:
        raise ValueError(
            "apply_ablation() requires a graph already processed by "
            "add_relation_types() (no .edge_type found)"
        )

    keep_relation_id = _ABLATION_TO_KEPT_RELATION_ID[ablation]
    mask = data.edge_type == keep_relation_id

    filtered_edge_index = data.edge_index[:, mask]
    filtered_edge_type = data.edge_type[mask]
    if filtered_edge_index.numel() == 0:
        # No edges of the kept relation exist in this specific graph
        # (e.g. a news item nobody retweeted, so it has no
        # direct_share edges either) -- an empty-but-correctly-shaped
        # [2, 0] edge_index, not a malformed one, so downstream
        # RGCNConv/batching still works (see the missing-data fallback
        # test in tests/ml_integrity/test_integrity.py for the
        # single-node-graph case this mirrors).
        filtered_edge_index = torch.empty((2, 0), dtype=torch.long)
        filtered_edge_type = torch.empty((0,), dtype=torch.long)

    new_data = Data(x=data.x, edge_index=filtered_edge_index, y=getattr(data, "y", None))
    new_data.edge_type = filtered_edge_type
    new_data.num_nodes = data.num_nodes
    return new_data
