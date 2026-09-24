"""
ML Inference schemas — Phases.md Phase 4, Architecture.md §4 `analyses`
columns this eventually feeds (verdict, raw_score, confidence_band,
is_calibrated_prob, propagation_available, interaction_available).

This module has no torch/DB import at all -- it's just the plain data
shape, so callers (tests, future Phase 5 orchestration) can use it
without pulling in the heavy ML stack.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AttributionData:
    """Attribution/evidence signals the model architecture actually
    produces. Rules.md §1 Rule 6 / PRD §4.5 revision 6 (attribution
    honesty): every field here must come from a real computation on
    the real forward pass, or be left at its empty default -- never
    filled with a plausible-looking placeholder to satisfy a UI
    contract. The current DualLayerGNN (RGCNConv-based, no attention
    mechanism) does not produce per-node or per-edge attribution
    scores, so `node_scores`/`edge_scores` are correctly empty for
    this architecture version, not merely unpopulated by omission.
    """

    node_scores: dict[int, float] = field(default_factory=dict)
    edge_scores: dict[tuple[int, int], float] = field(default_factory=dict)
    note: str = (
        "This model version (RGCNConv-based DualLayerGNN) does not produce "
        "per-node or per-edge attention scores. node_scores/edge_scores are "
        "intentionally empty, not omitted or approximated."
    )


@dataclass(frozen=True)
class PredictionResult:
    """Phase 4's exit-gate shape (Phases.md): verdict, raw score,
    confidence band via fixed thresholds, attribution data, and the
    two availability flags PRD §4.3's content-only fallback requires.
    """

    verdict: str  # "fake" | "real" -- matches analyses.verdict (Architecture.md §4)
    raw_score: float  # P(Fake), the model's own sigmoid output, 0..1
    confidence_band: str  # "low" | "moderate" | "high"
    is_calibrated_prob: bool  # Rules.md §6: False until calibration exists for this model_version
    attribution: AttributionData
    model_version: str
    propagation_available: bool
    interaction_available: bool


# Batch K's example thresholds (Phases.md Phase 3), used as-is since no
# real calibration study has been run yet for any model_version -- per
# Rules.md §6, is_calibrated_prob stays False regardless, so these
# bands are documented as "model confidence score" bands, not
# calibrated probability bands, until a real calibration pass changes
# that for a specific model_version.
CONFIDENCE_BAND_THRESHOLDS = {"low": 0.0, "moderate": 0.60, "high": 0.80}


def confidence_band_for_score(score: float) -> str:
    """Bands reflect confidence in the PREDICTED class, not raw P(Fake)
    directly -- a score of 0.05 means high confidence the article is
    Real, not low confidence. Confidence = max(score, 1 - score)."""
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"score must be in [0, 1], got {score}")
    confidence = max(score, 1.0 - score)
    if confidence >= CONFIDENCE_BAND_THRESHOLDS["high"]:
        return "high"
    if confidence >= CONFIDENCE_BAND_THRESHOLDS["moderate"]:
        return "moderate"
    return "low"
