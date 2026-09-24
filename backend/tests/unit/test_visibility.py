from app.analysis_orchestration.visibility import (
    contains_personal_markers,
    decide_visibility,
    is_publicly_fetchable,
)
from app.core.config import get_settings

_settings = get_settings()


def test_file_uploads_are_never_shared():
    assert (
        decide_visibility(
            input_type="file", source_url=None, canonical_text="x" * 100, settings=_settings
        )
        == "private"
    )


def test_pasted_text_is_always_private_no_verifiable_source():
    assert (
        decide_visibility(
            input_type="text",
            source_url=None,
            canonical_text="A long enough article body here " * 5,
            settings=_settings,
        )
        == "private"
    )


def test_public_url_without_personal_markers_is_shared():
    neutral_text = " ".join(["report finding data study"] * 10)
    assert (
        decide_visibility(
            input_type="url",
            source_url="https://example.com/article",
            canonical_text=neutral_text,
            settings=_settings,
        )
        == "shared"
    )


def test_url_without_source_url_is_private():
    assert (
        decide_visibility(
            input_type="url", source_url=None, canonical_text="x" * 100, settings=_settings
        )
        == "private"
    )


def test_short_text_stays_conservative_private():
    assert contains_personal_markers("too short", _settings) is True


def test_first_person_dense_text_flagged_personal():
    text = " ".join(["I my me myself"] * 10)
    assert contains_personal_markers(text, _settings) is True


def test_email_pattern_flagged_personal():
    text = "Contact me at someone@example.com for details " * 3
    assert contains_personal_markers(text, _settings) is True


def test_is_publicly_fetchable_requires_a_real_url():
    assert is_publicly_fetchable("https://example.com") is True
    assert is_publicly_fetchable(None) is False
    assert is_publicly_fetchable("") is False
