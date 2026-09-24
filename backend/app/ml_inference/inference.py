"""
ML Inference forward pass -- Phases.md Phase 4.

Takes an already relation-typed graph (research/propagate_research/
graph/build_graph.py's add_relation_types output -- Shared
Preprocessing's job, Phase 2, not re-done here) and the loaded model
from model_loader.py, and produces a PredictionResult.
"""
from __future__ import annotations

from typing import Any

from app.ml_inference.model_loader import LoadedModel
from app.ml_inference.schemas import AttributionData, PredictionResult, confidence_band_for_score


def run_inference(graph: Any, loaded_model: LoadedModel) -> PredictionResult:
    """`graph` is a single PyG Data/Batch object already produced by
    add_relation_types() (has x, edge_index, edge_type, batch, ptr).
    Runs one forward pass in eval/no_grad mode -- no training-mode
    side effects, no gradient computation.
    """
    import torch

    model = loaded_model.model
    model.eval()
    with torch.no_grad():
        logits = model(graph.x, graph.edge_index, graph.edge_type, graph.batch, graph.ptr)
        raw_score = torch.sigmoid(logits).squeeze().item()

    # raw_score is P(Fake); polarity confirmed 1=Fake, 0=Real (Phase 3)
    verdict = "fake" if raw_score >= 0.5 else "real"
    band = confidence_band_for_score(raw_score)

    propagation_available, interaction_available = _relation_availability(graph)

    return PredictionResult(
        verdict=verdict,
        raw_score=raw_score,
        confidence_band=band,
        is_calibrated_prob=False,  # Rules.md §6: no calibration study exists yet
        attribution=AttributionData(),  # honestly empty -- see AttributionData docstring
        model_version=loaded_model.model_version,
        propagation_available=propagation_available,
        interaction_available=interaction_available,
    )


def _relation_availability(graph: Any) -> tuple[bool, bool]:
    """PRD §4.3's content-only fallback: honestly report whether the
    graph actually has any direct-share (propagation) or
    inherited-share (interaction) edges, per the relation-type
    constants add_relation_types() assigns -- not a guess, a real
    check of graph.edge_type."""
    from propagate_research.graph.build_graph import DIRECT_SHARE, INHERITED_SHARE, RELATION_TO_ID

    edge_type = graph.edge_type
    direct_id = RELATION_TO_ID[DIRECT_SHARE]
    inherited_id = RELATION_TO_ID[INHERITED_SHARE]
    propagation_available = bool((edge_type == direct_id).any().item())
    interaction_available = bool((edge_type == inherited_id).any().item())
    return propagation_available, interaction_available
