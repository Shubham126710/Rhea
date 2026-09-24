from app.shared_preprocessing.normalization import canonicalize, compute_content_hash


def test_smart_quotes_normalize_to_straight():
    assert canonicalize("\u201cHello\u201d and \u2018world\u2019") == '"Hello" and \'world\''


def test_primes_normalize_to_straight_quotes():
    assert canonicalize("5\u2032 10\u2033") == "5' 10\""


def test_dash_family_normalizes_to_hyphen():
    text = "em\u2014dash en\u2013dash bar\u2015here minus\u2212sign"
    assert canonicalize(text) == "em-dash en-dash bar-here minus-sign"


def test_nbsp_and_unusual_spaces_become_regular_space():
    text = "a\u00a0b\u2003c\u2009d\u3000e"  # NBSP, em space, thin space, ideographic space
    assert canonicalize(text) == "a b c d e"


def test_nfc_normalization_applied():
    # "e" + combining acute accent (NFD) -> should canonicalize the
    # same as the single precomposed "é" (NFC) character.
    nfd = "cafe\u0301"
    nfc = "caf\u00e9"
    assert canonicalize(nfd) == canonicalize(nfc)


def test_whitespace_runs_collapse_to_single_space():
    assert canonicalize("a   b\n\nc\t\td") == "a b c d"


def test_leading_and_trailing_whitespace_stripped():
    assert canonicalize("   hello world   ") == "hello world"


def test_no_case_folding():
    assert canonicalize("Apple") != canonicalize("apple")
    assert canonicalize("Apple") == "Apple"


def test_order_typographic_then_nfc_then_collapse_then_strip():
    # A non-breaking space adjacent to smart quotes and a literal
    # double space should all collapse correctly in one pass,
    # demonstrating the steps compose in the documented order.
    text = "  \u201cHello\u00a0\u00a0world\u201d  "
    assert canonicalize(text) == '"Hello world"'


def test_content_hash_is_deterministic():
    canonical = canonicalize("The quick brown fox")
    assert compute_content_hash(canonical) == compute_content_hash(canonical)


def test_content_hash_is_sha256_hex():
    digest = compute_content_hash("hello")
    assert len(digest) == 64
    int(digest, 16)  # raises ValueError if not valid hex


def test_content_hash_differs_for_different_text():
    a = compute_content_hash(canonicalize("Article A"))
    b = compute_content_hash(canonicalize("Article B"))
    assert a != b


def test_content_hash_same_for_differently_formatted_equivalent_text():
    # Same article, differently sourced/whitespaced/quoted — this is
    # the property the Phase 2 exit gate depends on.
    a = canonicalize("The \u201cbig\u201d news\u2014today.\n\nMore text.")
    b = canonicalize("The   \"big\"   news-today.   More text.")
    assert compute_content_hash(a) == compute_content_hash(b)
