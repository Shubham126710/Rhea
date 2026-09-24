"""Builds the EvidencePayload the LLM Adapter receives — the single
place pipeline output gets translated into LLM input, so there's
exactly one seam to audit for evidence leakage (Rules.md §1 Rule 5)."""
from __future__ import annotations

from app.llm_adapter.schemas import EvidencePayload
from app.ml_inference.schemas import PredictionResult


def build_evidence_payload(
    prediction: PredictionResult, *, graph_node_count: int | None
) -> EvidencePayload:
    return EvidencePayload(
        verdict=prediction.verdict,
        confidence_band=prediction.confidence_band,
        is_calibrated_prob=prediction.is_calibrated_prob,
        propagation_available=prediction.propagation_available,
        interaction_available=prediction.interaction_available,
        attribution_note=prediction.attribution.note,
        graph_node_count=graph_node_count,
    )
