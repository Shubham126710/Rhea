"""Thin RQ job wrappers — no business logic, so pipeline.py and the
Phase 6 adapter stay testable without a real queue."""
from __future__ import annotations

from app.core.queue import analysis_queue, explanation_queue


def enqueue_analysis(analysis_id: str) -> None:
    analysis_queue().enqueue(
        "app.analysis_orchestration.pipeline.run_analysis_pipeline", analysis_id
    )


def enqueue_explanation(analysis_id: str) -> None:
    explanation_queue().enqueue(
        "app.analysis_orchestration.pipeline.run_explanation_stage", analysis_id
    )
