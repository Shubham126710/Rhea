"""
LLM provider abstraction — Architecture.md §3: "kept behind an
adapter/service layer so it's swappable." Justified per Rules.md
§3.1's own worked example (the LLM Adapter is explicitly named there
as the case where provider abstraction earns its keep).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.llm_adapter.schemas import EvidencePayload


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    tokens_used: int


class LLMProvider(Protocol):
    def generate(self, evidence: EvidencePayload, *, schema_json: dict) -> ProviderResponse: ...


class NoAPIKeyConfiguredProvider:
    """Used when GEMINI_API_KEY is unset — fails loudly and
    immediately rather than silently returning a fabricated
    explanation (Rules.md §1 Rule 2). Same honesty pattern as Phase
    1's ConsoleDevEmailSender / Phase 5's FeatureConstructionNotResolved."""

    def generate(self, evidence: EvidencePayload, *, schema_json: dict) -> ProviderResponse:
        raise RuntimeError(
            "No GEMINI_API_KEY configured — cannot generate a real explanation. "
            "Refusing to fabricate one."
        )
