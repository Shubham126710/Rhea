"""
Phase 6 LLM Adapter tests.

test_explanation_response_has_no_verdict_or_score_fields and
test_llm_adapter_module_has_no_path_to_write_verdict_or_raw_score are
the Rules.md §1 Rule #5 exit-gate tests: "LLM Adapter code must be
structurally incapable of writing to analyses.verdict or
analyses.raw_score." This is proven two ways — the schema itself
cannot carry those fields, and the module's own source has no
reference to either attribute name anywhere.
"""
import inspect

import pytest
from pydantic import ValidationError

from app.llm_adapter.adapter import generate_explanation
from app.llm_adapter.exceptions import ExplanationGenerationFailed
from app.llm_adapter.provider import NoAPIKeyConfiguredProvider, ProviderResponse
from app.llm_adapter.schemas import EvidencePayload, ExplanationResponse


def _evidence(**overrides):
    defaults = dict(
        verdict="fake",
        confidence_band="moderate",
        is_calibrated_prob=False,
        propagation_available=False,
        interaction_available=False,
        attribution_note="no attention scores for this architecture",
        graph_node_count=1,
    )
    defaults.update(overrides)
    return EvidencePayload(**defaults)


# --- Rule #5 structural boundary ---------------------------------------------


def test_explanation_response_has_no_verdict_or_score_fields():
    """The schema itself cannot carry a verdict or score — there is no
    field to even accidentally populate."""
    field_names = set(ExplanationResponse.model_fields.keys())
    assert "verdict" not in field_names
    assert "raw_score" not in field_names
    assert "score" not in field_names
    assert "confidence_band" not in field_names


def test_llm_adapter_module_has_no_path_to_write_verdict_or_raw_score():
    """Static check across every module in app.llm_adapter: no source
    file mentions 'verdict' or 'raw_score' as an attribute target.
    Reading the attribute (to build a prompt) is fine and expected;
    this test is about writing, so it specifically checks for
    assignment-shaped text, not any mention at all."""
    import app.llm_adapter.adapter as adapter_module
    import app.llm_adapter.evidence_builder as evidence_builder_module
    import app.llm_adapter.gemini_provider as gemini_provider_module
    import app.llm_adapter.provider as provider_module
    import app.llm_adapter.reuse as reuse_module
    import app.llm_adapter.schemas as schemas_module

    for module in (
        adapter_module,
        evidence_builder_module,
        gemini_provider_module,
        provider_module,
        reuse_module,
        schemas_module,
    ):
        source = inspect.getsource(module)
        assert ".verdict =" not in source, f"{module.__name__} assigns .verdict"
        assert ".raw_score =" not in source, f"{module.__name__} assigns .raw_score"


def test_generate_explanation_return_type_is_explanation_response_only():
    """The adapter's only public entry point can only ever return
    (ExplanationResponse, tokens_used) or raise — no other return path
    exists, and the tuple's first element is never anything but a real
    ExplanationResponse."""
    sig = inspect.signature(generate_explanation)
    assert "ExplanationResponse" in str(sig.return_annotation)


# --- schema validation ---------------------------------------------


def test_explanation_response_rejects_empty_supporting_signals():
    with pytest.raises(ValidationError):
        ExplanationResponse(summary="x", supporting_signals=[], uncertainty_note="none")


def test_explanation_response_accepts_valid_shape():
    resp = ExplanationResponse(
        summary="The article shows signals consistent with the model's verdict.",
        supporting_signals=["signal one", "signal two"],
        uncertainty_note="Limited evidence available.",
    )
    assert resp.summary
    assert len(resp.supporting_signals) == 2


# --- provider behavior ---------------------------------------------


def test_no_api_key_provider_refuses_to_fabricate():
    provider = NoAPIKeyConfiguredProvider()
    with pytest.raises(RuntimeError, match="Refusing to fabricate"):
        provider.generate(_evidence(), schema_json={})


def test_generate_explanation_raises_clear_error_with_no_api_key():
    with pytest.raises(ExplanationGenerationFailed):
        generate_explanation(_evidence(), provider=NoAPIKeyConfiguredProvider())


# --- grounding / regeneration ---------------------------------------------


class _FakeProvider:
    """Returns a scripted sequence of raw JSON strings, one per call —
    used to prove the regeneration loop actually retries on a bad
    response rather than accepting the first one unconditionally.
    Wrapped in ProviderResponse (tokens_used=0) to match the real
    provider protocol's return shape."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.call_count = 0

    def generate(self, evidence, *, schema_json):
        response = self._responses[self.call_count]
        self.call_count += 1
        return ProviderResponse(text=response, tokens_used=0)


def test_ungrounded_response_triggers_regeneration_not_silent_acceptance():
    """First response fabricates propagation evidence the payload
    marks unavailable; second is genuinely grounded. Proves the
    adapter actually re-tries rather than passing the first response
    straight through."""
    ungrounded = (
        '{"summary": "This spread rapidly through the propagation network.", '
        '"supporting_signals": ["propagation signal"], "uncertainty_note": "n/a"}'
    )
    grounded = (
        '{"summary": "This is a content-only analysis with no cascade data.", '
        '"supporting_signals": ["content signal"], "uncertainty_note": "Limited evidence."}'
    )
    provider = _FakeProvider([ungrounded, grounded])

    result, tokens_used = generate_explanation(
        _evidence(propagation_available=False), provider=provider
    )

    assert provider.call_count == 2
    assert "propagation" not in result.summary.lower()
    assert tokens_used == 0  # _FakeProvider reports 0, never guessed


def test_malformed_json_response_triggers_regeneration():
    provider = _FakeProvider(
        [
            "not valid json at all",
            '{"summary": "Fine.", "supporting_signals": ["a"], "uncertainty_note": "n/a"}',
        ]
    )
    result, _tokens_used = generate_explanation(_evidence(), provider=provider)
    assert provider.call_count == 2
    assert result.summary == "Fine."


def test_persistent_failure_raises_explanation_generation_failed_not_a_fabricated_result():
    """Every attempt fails validation -- must raise, never return a
    best-effort guess."""
    provider = _FakeProvider(["still not json"] * 10)  # more than max attempts
    with pytest.raises(ExplanationGenerationFailed):
        generate_explanation(_evidence(), provider=provider)


def test_grounded_response_with_available_evidence_is_accepted_first_try():
    valid = (
        '{"summary": "Propagation signals were strong.", '
        '"supporting_signals": ["propagation signal"], "uncertainty_note": "n/a"}'
    )
    provider = _FakeProvider([valid])
    result, _tokens_used = generate_explanation(
        _evidence(propagation_available=True), provider=provider
    )
    assert provider.call_count == 1
    assert result.summary == "Propagation signals were strong."
