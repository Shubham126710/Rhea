"""Explanation reuse policy — Architecture.md §6.4: cached and reused
unless the underlying model/evidence version changed."""
from __future__ import annotations


def should_regenerate_explanation(analysis) -> bool:
    if analysis.explanation is None:
        return True
    stored_model_version = analysis.explanation.get("_generated_for_model_version")
    return stored_model_version != analysis.model_version
