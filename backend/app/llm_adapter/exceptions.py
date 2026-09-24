"""LLM Adapter domain exceptions."""


class ExplanationGenerationFailed(Exception):
    """Raised when the provider call fails or the response fails
    schema/evidence-grounding validation after all retry attempts.
    Callers must render 'Explanation unavailable' — never fabricate
    one (Rules.md §1 Rule 2)."""


class UngroundedResponse(Exception):
    """Raised internally when a structured response references
    evidence not present in the payload it was given — triggers a
    regeneration attempt, not a silent pass-through."""
