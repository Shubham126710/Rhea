"""
Live graph/feature construction — blueprint §3.3, Blocker 1 (§15).

This is the ONE place live content becomes a relation-typed graph.
Every other file calls only build_live_graph(), never touches feature
construction directly — so the unresolved research-methodology
decision below has exactly one seam to patch once it's made, not a
scattered set of assumptions.

WHAT IS GENUINELY UNRESOLVED (not invented around): the trained
model's in_channels was fixed by whichever UPFD feature type
(profile/spacy/bert/content) Phase 3 locked. No component in this
repository reproduces that same encoding for arbitrary live text —
content_encoder.py is explicitly documented as unrelated to GNN
root-node features (used only by the Text-Encoder+MLP baseline). This
function does NOT pad, truncate, project, or otherwise force a
different-width vector to fit. It raises FeatureConstructionNotResolved
with a clear, specific message instead. Resolving this requires an
explicit research-methodology decision from the project owner (see
blueprint §15, Blocker 1) — not a default picked here.
"""
from __future__ import annotations


class FeatureConstructionNotResolved(Exception):
    """Raised by build_live_graph() until Blocker 1 is resolved. A
    caller catching this should surface a clear, user-facing 'analysis
    unavailable' message — never a silent hang, never a fabricated
    result."""


def build_live_graph(canonical_text: str, *, expected_in_channels: int):
    """Would return a relation-typed PyG Data/Batch object (single
    root node, no edges — PRD §4.3's content-only fallback shape) if
    a verified, reproducible way existed to encode `canonical_text`
    into an `expected_in_channels`-wide vector matching the trained
    model's actual training-time feature space. It does not exist in
    this repository yet."""
    raise FeatureConstructionNotResolved(
        f"No verified way exists to construct a {expected_in_channels}-dim "
        f"live feature vector matching the trained model's feature space "
        f"(Blocker 1, unresolved research-methodology decision). This "
        f"analysis cannot be completed until that decision is made — see "
        f"the Phase 5-9 blueprint §15."
    )
