"""
Phase 6 structured I/O schemas — Architecture.md §3/§6.4.

EvidencePayload is the ONLY thing the LLM ever sees: pipeline outputs
already computed by ML Inference, never raw article text re-fed for
independent judgment (Rules.md §1 Rule 5 — the GNN predicts, the LLM
only explains). ExplanationResponse is schema-validated on the way
back, not trusted as free text.
"""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class EvidencePayload(BaseModel):
    verdict: str
    confidence_band: str
    is_calibrated_prob: bool
    propagation_available: bool
    interaction_available: bool
    attribution_note: str
    graph_node_count: int | None = None


class ExplanationResponse(BaseModel):
    summary: str
    supporting_signals: list[str]
    uncertainty_note: str

    @field_validator("supporting_signals")
    @classmethod
    def _at_least_one_signal(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("supporting_signals must not be empty")
        return v
