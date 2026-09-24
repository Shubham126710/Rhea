import pytest
from propagate_research.data.upfd_loader import (
    PUBLISHED_GRAPH_COUNTS,
    UPFDLoadConfig,
    assert_label_polarity_plausible,
    load_upfd_split,
    manual_download_instructions,
)

# --- UPFDLoadConfig validation (pure Python, no torch) ---


def test_valid_config_accepted():
    config = UPFDLoadConfig(root="/tmp/data", name="politifact", feature="bert")
    assert config.name == "politifact"


def test_default_feature_is_bert():
    config = UPFDLoadConfig(root="/tmp/data", name="gossipcop")
    assert config.feature == "bert"


def test_invalid_name_rejected():
    with pytest.raises(ValueError):
        UPFDLoadConfig(root="/tmp/data", name="not_a_real_dataset")


def test_invalid_feature_rejected():
    with pytest.raises(ValueError):
        UPFDLoadConfig(root="/tmp/data", name="politifact", feature="not_a_real_feature")


# --- load_upfd_split: only the graceful-failure path is testable here ---


def test_load_upfd_split_raises_clear_error_when_download_unreachable(tmp_path, monkeypatch):
    # Mocked at the actual external seam (torch_geometric.datasets.UPFD)
    # rather than relying on this environment's network being
    # unreachable -- deterministic regardless of whether UPFD happens
    # to be cached or downloadable here. Exercises the same production
    # except-and-wrap path in upfd_loader.load_upfd_split either way.
    import torch_geometric.datasets as tgd

    def _raise_network_error(*args, **kwargs):
        raise OSError("simulated: network unreachable")

    monkeypatch.setattr(tgd, "UPFD", _raise_network_error)

    config = UPFDLoadConfig(root=str(tmp_path), name="politifact")
    with pytest.raises(RuntimeError, match="Could not load UPFD"):
        load_upfd_split(config, "train")


def test_load_upfd_split_rejects_invalid_split_before_import():
    config = UPFDLoadConfig(root="/tmp/data", name="politifact")
    with pytest.raises(ValueError):
        load_upfd_split(config, "not_a_real_split")


# --- manual_download_instructions ---


def test_manual_download_instructions_mentions_raw_dir():
    config = UPFDLoadConfig(root="/tmp/data", name="politifact", feature="bert")
    msg = manual_download_instructions(config)
    assert "politifact" in msg
    assert "raw" in msg


# --- label-polarity plausibility check ---
#
# Both real UPFD domains are exactly balanced (politifact 157/157,
# gossipcop 2732/2732, corrected -- see upfd_loader.py's
# PUBLISHED_GRAPH_COUNTS). That symmetry is itself the reason this
# distribution-only check can never establish which polarity is
# correct for either real domain: a 50/50 split looks equally
# plausible under both. The tests below reflect that honestly instead
# of pretending gossipcop is a skewed case to test against -- the
# check's actual discriminating behavior (rejecting a genuinely
# skewed distribution) is tested separately below via
# _fraction_within_tolerance directly, decoupled from any specific
# UPFD domain.


def test_label_polarity_matches_published_fake_as_one_for_balanced_domain():
    # gossipcop is now known to be exactly balanced (2732/2732) -- a
    # 50/50 label split is plausible whether 1 or 0 is Fake, which is
    # exactly the property that makes distribution alone insufficient
    # to establish polarity (see upfd_loader.py's module docstring).
    labels = [1] * 2732 + [0] * 2732
    assert_label_polarity_plausible(labels, "gossipcop")  # should not raise


def test_label_polarity_matches_published_fake_as_zero_for_balanced_domain():
    labels = [0] * 2732 + [1] * 2732  # reversed polarity, still plausible
    assert_label_polarity_plausible(labels, "gossipcop")  # should not raise


def test_label_polarity_rejects_implausible_split():
    # A 99%-one-class label set is far from 50/50 under either
    # polarity, for either real UPFD domain -- this should reject
    # regardless of which domain's expected counts are used.
    labels = [1] * 990 + [0] * 10
    with pytest.raises(ValueError):
        assert_label_polarity_plausible(labels, "gossipcop")


def test_label_polarity_rejects_unknown_dataset_name():
    with pytest.raises(ValueError):
        assert_label_polarity_plausible([0, 1], "not_a_real_dataset")


def test_label_polarity_rejects_empty_labels():
    with pytest.raises(ValueError):
        assert_label_polarity_plausible([], "politifact")


def test_label_polarity_rejects_non_binary_labels():
    with pytest.raises(ValueError):
        assert_label_polarity_plausible([0, 1, 2], "politifact")


def test_label_polarity_politifact_balanced_case():
    # politifact's published counts are exactly 157/157 -- both
    # polarities of a balanced synthetic sample should pass. Same
    # situation as gossipcop now (see the section comment above).
    labels = [1] * 157 + [0] * 157
    assert_label_polarity_plausible(labels, "politifact")  # should not raise


def test_gossipcop_published_counts_are_balanced():
    """Documents the corrected data as a fact this test file's
    reasoning depends on -- if PUBLISHED_GRAPH_COUNTS ever changes,
    this makes the dependency explicit rather than silently stale."""
    gossipcop = PUBLISHED_GRAPH_COUNTS["gossipcop"]
    assert gossipcop["fake"] == gossipcop["real"]
    assert gossipcop["fake"] + gossipcop["real"] == gossipcop["total"]


def test_fraction_within_tolerance_discriminates_genuinely_skewed_distributions():
    """The plausibility check's actual discriminating power (rejecting
    a genuinely skewed distribution against a genuinely skewed
    expectation) can no longer be demonstrated using gossipcop as the
    real-world example, since it's balanced. Tested directly against
    the underlying primitive instead, with a synthetic skewed
    expectation decoupled from any specific UPFD domain."""
    from propagate_research.data.upfd_loader import _fraction_within_tolerance

    # 30% positive rate observed, expected ~30% -- plausible
    assert _fraction_within_tolerance(300, 1000, 300, 1000) is True
    # 90% positive rate observed, expected ~30% -- not plausible
    assert _fraction_within_tolerance(900, 1000, 300, 1000) is False
