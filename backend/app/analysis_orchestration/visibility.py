"""
Visibility-promotion policy — Architecture.md §6.1, Phases.md Phase 5.

Pure function, no DB/IO. Default private on any ambiguity. Thresholds
are config-tunable (Architecture §12) but the shape of the rule itself
requires Rules.md §1 Rule 4 sign-off to change, since it touches
privacy.
"""
from __future__ import annotations

import re

from app.core.config import Settings

_FIRST_PERSON_PATTERN = re.compile(r"\b(i|me|my|mine|myself)\b", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_PATTERN = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")


def is_publicly_fetchable(source_url: str | None) -> bool:
    """A URL submission is only eligible for shared visibility if it
    has a real, recorded public source — conservative by construction,
    since Analysis Orchestration has no independent way to verify a
    URL was genuinely publicly reachable beyond having fetched it."""
    return bool(source_url)


def contains_personal_markers(canonical_text: str, settings: Settings) -> bool:
    """Conservative heuristic: first-person density above threshold,
    or any email/phone pattern present. Too short a text to judge
    meaningfully stays conservative (personal=True) rather than risk
    a false-negative on brief, personal content."""
    words = canonical_text.split()
    if len(words) < settings.VISIBILITY_PERSONAL_MARKER_MIN_WORDS_FOR_CHECK:
        return True
    if _EMAIL_PATTERN.search(canonical_text) or _PHONE_PATTERN.search(canonical_text):
        return True
    first_person_count = len(_FIRST_PERSON_PATTERN.findall(canonical_text))
    density = first_person_count / len(words)
    return density > settings.VISIBILITY_PERSONAL_MARKER_FIRST_PERSON_DENSITY


def decide_visibility(
    *, input_type: str, source_url: str | None, canonical_text: str, settings: Settings
) -> str:
    """Returns 'private' or 'shared'."""
    if input_type == "file":
        return "private"  # PRD §4.8: files never eligible, regardless of anything else
    if input_type == "url" and not is_publicly_fetchable(source_url):
        return "private"
    if input_type == "text":
        return "private"  # no verifiable public source for pasted text
    if contains_personal_markers(canonical_text, settings):
        return "private"
    return "shared"
