import numpy as np
import pytest
from propagate_research.evaluate.metrics import compute_metrics, compute_metrics_by_domain


def test_perfect_predictions_score_1_everywhere():
    y_true = [0, 1, 0, 1]
    y_pred = [0, 1, 0, 1]
    y_score = [0.1, 0.9, 0.2, 0.8]
    report = compute_metrics(y_true, y_pred, y_score)
    assert report.accuracy == 1.0
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.f1 == 1.0
    assert report.roc_auc == 1.0
    assert report.pr_auc == 1.0
    assert report.specificity == 1.0


def test_all_wrong_predictions():
    y_true = [0, 1]
    y_pred = [1, 0]
    report = compute_metrics(y_true, y_pred)
    assert report.accuracy == 0.0
    assert report.confusion_matrix == [[0, 1], [1, 0]]


def test_confusion_matrix_shape_and_values():
    # tn=2, fp=1, fn=0, tp=1
    y_true = [0, 0, 0, 1]
    y_pred = [0, 0, 1, 1]
    report = compute_metrics(y_true, y_pred)
    assert report.confusion_matrix == [[2, 1], [0, 1]]
    assert report.specificity == pytest.approx(2 / 3)


def test_roc_auc_none_without_scores():
    report = compute_metrics([0, 1], [0, 1])
    assert report.roc_auc is None
    assert report.pr_auc is None


def test_roc_auc_none_when_only_one_class_present():
    report = compute_metrics([1, 1, 1], [1, 1, 0], y_score=[0.9, 0.8, 0.3])
    assert report.roc_auc is None
    assert report.pr_auc is None


def test_empty_input_raises():
    with pytest.raises(ValueError):
        compute_metrics([], [])


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        compute_metrics([0, 1, 0], [0, 1])


def test_score_shape_mismatch_raises():
    with pytest.raises(ValueError):
        compute_metrics([0, 1], [0, 1], y_score=[0.1, 0.2, 0.3])


def test_n_samples_reported_correctly():
    report = compute_metrics([0, 1, 0, 1, 0], [0, 1, 0, 0, 0])
    assert report.n_samples == 5


def test_as_dict_round_trips_all_fields():
    report = compute_metrics([0, 1], [0, 1], y_score=[0.1, 0.9])
    d = report.as_dict()
    assert set(d.keys()) == {
        "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc",
        "specificity", "confusion_matrix", "n_samples",
    }


def test_specificity_nan_when_no_negatives_present():
    report = compute_metrics([1, 1], [1, 1])
    assert np.isnan(report.specificity)


# --- per-domain / aggregate ---


def test_per_domain_and_aggregate_reports_present():
    y_true = [0, 1, 0, 1, 0, 1]
    y_pred = [0, 1, 0, 0, 0, 1]
    domains = ["politifact", "politifact", "politifact", "gossipcop", "gossipcop", "gossipcop"]
    report = compute_metrics_by_domain(y_true, y_pred, domains)
    assert set(report.per_domain.keys()) == {"politifact", "gossipcop"}
    assert report.aggregate is not None
    assert report.aggregate.n_samples == 6


def test_per_domain_metrics_computed_independently():
    # politifact: all correct; gossipcop: all wrong
    y_true = [0, 1, 0, 1]
    y_pred = [0, 1, 1, 0]
    domains = ["politifact", "politifact", "gossipcop", "gossipcop"]
    report = compute_metrics_by_domain(y_true, y_pred, domains)
    assert report.per_domain["politifact"].accuracy == 1.0
    assert report.per_domain["gossipcop"].accuracy == 0.0


def test_domain_length_mismatch_raises():
    with pytest.raises(ValueError):
        compute_metrics_by_domain([0, 1], [0, 1], ["a"])


def test_domain_report_as_dict():
    y_true = [0, 1]
    y_pred = [0, 1]
    domains = ["politifact", "gossipcop"]
    report = compute_metrics_by_domain(y_true, y_pred, domains)
    d = report.as_dict()
    assert "per_domain" in d and "aggregate" in d
    assert set(d["per_domain"].keys()) == {"politifact", "gossipcop"}
