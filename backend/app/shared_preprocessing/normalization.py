"""
Text canonicalization and content_hash.

APPROVED NORMALIZATION RULE (applied in this exact order — this is the
spec, not a summary of it):

  1. Typographic normalization:
       a. Smart/curly quotes and primes -> straight ASCII equivalents:
          single-quote family (U+2018 U+2019 U+201A U+201B U+2032) -> '
          double-quote family (U+201C U+201D U+201E U+201F U+2033) -> "
       b. Em dash, en dash, horizontal bar, minus sign
          (U+2014 U+2013 U+2015 U+2212) -> '-' (consistent single form)
       c. Any Unicode "space separator" character (category Zs — this
          includes the ordinary ASCII space as well as non-breaking
          space U+00A0 and the other unusual space-width characters
          such as U+2000-U+200A, U+202F, U+205F, U+3000) -> a regular
          ASCII space ' '
  2. Unicode NFC normalization (unicodedata.normalize("NFC", text)) —
     applied AFTER step 1, so the ASCII characters step 1 just produced
     are the ones NFC folds equivalent representations toward.
  3. Whitespace collapsing: any run of one or more whitespace
     characters (space, tab, newline, etc. — regex \\s+) collapses to
     a single ASCII space.
  4. Leading/trailing whitespace stripped.

No case folding at any step (explicitly out of scope per the approved
plan) — "Apple" and "apple" normalize to different text and therefore
hash differently.

content_hash is the SHA-256 hex digest of the canonicalized text,
UTF-8 encoded. input_type is never part of the hash (Architecture.md
§4) — only the canonical text itself.
"""
import hashlib
import re
import unicodedata

_SINGLE_QUOTE_FAMILY = "\u2018\u2019\u201a\u201b\u2032"
_DOUBLE_QUOTE_FAMILY = "\u201c\u201d\u201e\u201f\u2033"
_DASH_FAMILY = "\u2014\u2013\u2015\u2212"

_TYPOGRAPHIC_MAP: dict[str, str] = {
    **{ch: "'" for ch in _SINGLE_QUOTE_FAMILY},
    **{ch: '"' for ch in _DOUBLE_QUOTE_FAMILY},
    **{ch: "-" for ch in _DASH_FAMILY},
}

_WHITESPACE_RUN_RE = re.compile(r"\s+")


def _typographic_normalize(text: str) -> str:
    out = []
    for ch in text:
        if ch in _TYPOGRAPHIC_MAP:
            out.append(_TYPOGRAPHIC_MAP[ch])
        elif unicodedata.category(ch) == "Zs":
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def canonicalize(text: str) -> str:
    """Steps 1-4 of the approved normalization rule, in order."""
    text = _typographic_normalize(text)
    text = unicodedata.normalize("NFC", text)
    text = _WHITESPACE_RUN_RE.sub(" ", text)
    return text.strip()


def compute_content_hash(canonical_text: str) -> str:
    """SHA-256 hex digest of already-canonicalized text. Callers must
    pass text that has already been through canonicalize() — this
    function does not re-normalize, so it can be unit-tested against
    the hash independently of the normalization step."""
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
