"""Phase 5 request/response schemas — Architecture.md §5."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SubmitAnalysisRequest(BaseModel):
    # file uploads use the separate multipart endpoint
    input_type: str = Field(pattern="^(text|url)$")
    text: str | None = None
    url: str | None = None

    @model_validator(mode="after")
    def _exactly_one_content_field(self) -> SubmitAnalysisRequest:
        if self.input_type == "text" and not self.text:
            raise ValueError("text is required when input_type is 'text'")
        if self.input_type == "url" and not self.url:
            raise ValueError("url is required when input_type is 'url'")
        return self


class SubmitAnalysisResponse(BaseModel):
    analysis_reference_id: UUID
    status: str


class AnalysisStatusResponse(BaseModel):
    status: str
    stage: str | None = None


class GraphSubsetResponse(BaseModel):
    """Mirrors app.graph_processor.filtering.GraphSubset exactly —
    no coordinates (Rules.md §2: graph layout never happens
    server-side). This is the smallest spec-consistent way to expose
    what Graph Processor already computes: reuse the existing shape
    verbatim rather than inventing a new one for the API."""

    node_ids: list[int]
    edges: list[tuple[int, int, int]]
    node_relevance: dict[str, float]
    root_index: int
    truncated: bool


class AnalysisResultResponse(BaseModel):
    analysis_reference_id: UUID
    verdict: str
    raw_score: float | None
    confidence_band: str
    is_calibrated_prob: bool
    model_version: str
    propagation_available: bool
    interaction_available: bool
    explanation: dict | None
    explanation_status: str | None
    attribution_note: str | None
    graph: GraphSubsetResponse | None
    visibility: str
    created_at: datetime


class MessageResponse(BaseModel):
    message: str


class HistoryItem(BaseModel):
    analysis_reference_id: UUID
    title: str | None
    verdict: str
    confidence_band: str
    processing_status: str
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int


class SearchResponse(BaseModel):
    items: list[HistoryItem]
