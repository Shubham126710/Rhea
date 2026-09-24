"""Duplicate detection — Architecture.md §6.2, Rules.md §2: the ONLY
place the five-value version tuple is used as a lookup key."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis


def find_existing_analysis(
    db: Session,
    *,
    content_hash: str,
    model_version: str,
    preprocessing_version: str,
    graph_construction_version: str,
    calibration_version: str,
) -> Analysis | None:
    return db.execute(
        select(Analysis).where(
            Analysis.content_hash == content_hash,
            Analysis.model_version == model_version,
            Analysis.preprocessing_version == preprocessing_version,
            Analysis.graph_construction_version == graph_construction_version,
            Analysis.calibration_version == calibration_version,
        )
    ).scalar_one_or_none()
