import numpy as np
import pytest
from propagate_research.evaluate.calibration import (
    assess_calibration,
    brier_score,
    expected_calibration_error,
    fit_temperature,
    reliability_diagram,
)


def test_brier_score_perfect_predictions_is_zero():
    assert brier_score([0, 1, 0, 1], [0.0, 1.0, 0.0, 1.0]) == 0.0


def test_brier_score_worst_case_predictions_is_one():
    assert brier_score([0, 1], [1.0, 0.0]) == pytest.approx(1.0)


def test_brier_score_uniform_uncertainty():
    assert brier_score([0, 1], [0.5, 0.5]) == pytest.approx(0.25)


def test_brier_score_shape_mismatch_raises():
    with pytest.raises(ValueError):
        brier_score([0, 1], [0.5])


def test_brier_score_empty_raises():
    with pytest.raises(ValueError):
        brier_score([], [])


def test_reliability_diagram_returns_n_bins_entries():
    y_true = [0, 1, 0, 1, 0]
    y_prob = [0.1, 0.9, 0.2, 0.8, 0.5]
    bins = reliability_diagram(y_true, y_prob, n_bins=10)
    assert len(bins) == 10


def test_reliability_diagram_empty_bins_have_none_values():
    bins = reliability_diagram([0, 1], [0.05, 0.95], n_bins=10)
    empty_bin = bins[5]  # 0.5-0.6 range, nothing falls there
    assert empty_bin.count == 0
    assert empty_bin.mean_predicted_prob is None
    assert empty_bin.empirical_accuracy is None


def test_reliability_diagram_perfect_calibration():
    # 10 samples all with p=0.7, 7 of them actually positive
    y_true = [1] * 7 + [0] * 3
    y_prob = [0.7] * 10
    bins = reliability_diagram(y_true, y_prob, n_bins=10)
    occupied = [b for b in bins if b.count > 0]
    assert len(occupied) == 1
    assert occupied[0].mean_predicted_prob == pytest.approx(0.7)
    assert occupied[0].empirical_accuracy == pytest.approx(0.7)


def test_reliability_diagram_p_equals_one_falls_in_last_bin():
    bins = reliability_diagram([1], [1.0], n_bins=10)
    assert bins[-1].count == 1


def test_reliability_diagram_invalid_n_bins_raises():
    with pytest.raises(ValueError):
        reliability_diagram([0, 1], [0.1, 0.9], n_bins=0)


def test_expected_calibration_error_zero_for_perfect_calibration():
    y_true = [1] * 7 + [0] * 3
    y_prob = [0.7] * 10
    bins = reliability_diagram(y_true, y_prob, n_bins=10)
    ece = expected_calibration_error(bins, n_total=10)
    assert ece == pytest.approx(0.0, abs=1e-9)


def test_expected_calibration_error_positive_for_miscalibration():
    # predicts 0.9 confidence but only 50% accurate
    y_true = [1, 0, 1, 0]
    y_prob = [0.9, 0.9, 0.9, 0.9]
    bins = reliability_diagram(y_true, y_prob, n_bins=10)
    ece = expected_calibration_error(bins, n_total=4)
    assert ece == pytest.approx(0.4, abs=1e-9)  # |0.9 - 0.5|


def test_assess_calibration_returns_full_report():
    y_true = [0, 1, 0, 1, 0, 1, 0, 1]
    y_prob = [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6]
    report = assess_calibration(y_true, y_prob, n_bins=5)
    assert report.brier_score >= 0
    assert report.expected_calibration_error >= 0
    assert len(report.reliability_bins) == 5
    d = report.as_dict()
    assert "brier_score" in d and "reliability_bins" in d


def test_fit_temperature_recovers_reasonable_scale():
    # logits scaled by a known true temperature; fitted T should bring
    # sigmoid(logits/T_fit) close to well-calibrated probabilities
    rng = np.random.default_rng(0)
    true_probs = rng.uniform(0.05, 0.95, size=200)
    y_true = rng.binomial(1, true_probs)
    true_logits = np.log(true_probs / (1 - true_probs))
    overconfident_logits = true_logits * 3.0  # simulate overconfidence

    t = fit_temperature(y_true, overconfident_logits)
    assert t > 1.0  # should scale down an overconfident model


def test_fit_temperature_shape_mismatch_raises():
    with pytest.raises(ValueError):
        fit_temperature([0, 1], [0.5])


def test_fit_temperature_empty_raises():
    with pytest.raises(ValueError):
        fit_temperature([], [])
