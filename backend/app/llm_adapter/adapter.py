"""
Top-level LLM Adapter — Architecture.md §5/§6.4.

Structural boundary enforced here, not just by convention (Rules.md
§1 Rule 5): this module has no parameter, return path, or side
channel that could write to analyses.verdict or analyses.raw_score —
it only ever returns an ExplanationResponse, and pipeline.py's own
_run_explanation only ever assigns that to analyses.explanation.
"""
from __future__ import annotations

import json

from pydantic import ValidationError

from app.core.config import get_settings
from app.llm_adapter.exceptions import ExplanationGenerationFailed, UngroundedResponse
from app.llm_adapter.provider import LLMProvider, NoAPIKeyConfiguredProvider
from app.llm_adapter.schemas import EvidencePayload, ExplanationResponse

_EXPLANATION_SCHEMA_JSON = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "supporting_signals": {"type": "array", "items": {"type": "string"}},
        "uncertainty_note": {"type": "string"},
    },
    "required": ["summary", "supporting_signals", "uncertainty_note"],
}


def _get_provider() -> LLMProvider:
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        return NoAPIKeyConfiguredProvider()
    from app.llm_adapter.gemini_provider import GeminiProvider

    return GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.GEMINI_MODEL_NAME,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


def _check_grounded(response: ExplanationResponse, evidence: EvidencePayload) -> None:
    """Minimal grounding check: every claim about data availability
    must match what the evidence payload actually says — catches the
    most direct kind of fabrication (claiming propagation evidence
    exists when it doesn't), not a full faithfulness study."""
    text = (response.summary + " ".join(response.supporting_signals)).lower()
    no_prop = not evidence.propagation_available
    no_interact = not evidence.interaction_available
    if no_prop and "propagation" in text and "not available" not in text:
        raise UngroundedResponse("Response references propagation data marked unavailable")
    if no_interact and "interaction" in text and "not available" not in text:
        raise UngroundedResponse("Response references interaction data marked unavailable")


def generate_explanation(
    evidence: EvidencePayload, *, provider: LLMProvider | None = None
) -> tuple[ExplanationResponse, int]:
    """Returns (response, tokens_used) -- tokens_used is the real
    figure the provider reported for the successful call (0 for
    _FakeProvider/NoAPIKeyConfiguredProvider in tests, never guessed).
    Deliberately has no Redis/budget dependency of its own (Architecture.md
    §10's testing tiers: Redis is an integration-tier concern) --
    budget gating and recording are pipeline.py's job, since it's
    already the orchestration layer deciding whether to call this at
    all (should_regenerate_explanation lives there already)."""
    settings = get_settings()
    provider = provider or _get_provider()
    last_error: Exception | None = None

    for _attempt in range(settings.LLM_MAX_REGENERATION_ATTEMPTS + 1):
        try:
            result = provider.generate(evidence, schema_json=_EXPLANATION_SCHEMA_JSON)
            parsed = json.loads(result.text)
            response = ExplanationResponse(**parsed)
            _check_grounded(response, evidence)
            return response, result.tokens_used
        except (ValidationError, json.JSONDecodeError, UngroundedResponse) as exc:
            last_error = exc
            continue
        except Exception as exc:  # noqa: BLE001 -- provider-level failure (network, auth, no key)
            raise ExplanationGenerationFailed(str(exc)) from exc

    raise ExplanationGenerationFailed(
        f"Explanation failed schema/grounding validation after "
        f"{settings.LLM_MAX_REGENERATION_ATTEMPTS + 1} attempts: {last_error}"
    )
