"""
Full metric suite (Phases.md Batch K): Accuracy, Precision, Recall, F1,
ROC-AUC, PR-AUC, Specificity, confusion matrix — per-domain and
aggregate. Operates on plain arrays of true labels / predicted labels
/ predicted probabilities, so it has no dependency on torch or any
particular model — any component (baseline or GNN) that produces
predictions in this shape can be scored the same way.

Label convention: 1 = Fake, 0 = Real (binary, per the locked Phase 3
decision -- and independently confirmed against real UPFD data plus
FakeNewsNet ground truth; see data/upfd_loader.py's module docstring
for the evidence chain). Probabilities are P(Fake).
"""
from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass(frozen=True)
class MetricReport:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None  # None when y_true has only one class present
    pr_auc: float | None
    specificity: float
    confusion_matrix: list[list[int]]  # [[tn, fp], [fn, tp]]
    n_samples: int

    def as_dict(self) -> dict:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "pr_auc": self.pr_auc,
            "specificity": self.specificity,
            "confusion_matrix": self.confusion_matrix,
            "n_samples": self.n_samples,
        }


def compute_metrics(
    y_true: np.ndarray | list[int],
    y_pred: np.ndarray | list[int],
    y_score: np.ndarray | list[float] | None = None,
) -> MetricReport:
    """y_true/y_pred: 0/1 labels. y_score: predicted P(Fake), needed
    for ROC-AUC/PR-AUC — if omitted, those two fields are None rather
    than silently substituted with something misleading.

    Raises ValueError on empty input or length mismatch rather than
    letting sklearn's own (less specific) error surface, since a
    caller of a research pipeline benefits from a clear message here.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if y_true.shape[0] == 0:
        raise ValueError("Cannot compute metrics on empty input")
    if y_true.shape != y_pred.shape:
        raise ValueError(f"y_true shape {y_true.shape} != y_pred shape {y_pred.shape}")

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else float("nan")

    roc_auc = None
    pr_auc = None
    if y_score is not None:
        y_score = np.asarray(y_score)
        if y_score.shape != y_true.shape:
            raise ValueError(f"y_score shape {y_score.shape} != y_true shape {y_true.shape}")
        if len(np.unique(y_true)) > 1:
            roc_auc = float(roc_auc_score(y_true, y_score))
            pr_auc = float(average_precision_score(y_true, y_score))
        # else: ROC-AUC/PR-AUC are undefined with only one class present
        # in y_true (this happens on tiny dev-time smoke tests) -- left
        # as None rather than raising, since the rest of the report is
        # still meaningful.

    return MetricReport(
        accuracy=float(accuracy_score(y_true, y_pred)),
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, zero_division=0)),
        f1=float(f1_score(y_true, y_pred, zero_division=0)),
        roc_auc=roc_auc,
        pr_auc=pr_auc,
        specificity=specificity,
        confusion_matrix=cm.tolist(),
        n_samples=int(y_true.shape[0]),
    )


@dataclass(frozen=True)
class DomainMetricReport:
    """Per-domain reports plus an aggregate over the pooled samples
    (Phases.md: "per-domain and aggregate")."""

    per_domain: dict[str, MetricReport] = field(default_factory=dict)
    aggregate: MetricReport | None = None

    def as_dict(self) -> dict:
        return {
            "per_domain": {name: r.as_dict() for name, r in self.per_domain.items()},
            "aggregate": self.aggregate.as_dict() if self.aggregate else None,
        }


def compute_metrics_by_domain(
    y_true: np.ndarray | list[int],
    y_pred: np.ndarray | list[int],
    domains: np.ndarray | list[str],
    y_score: np.ndarray | list[float] | None = None,
) -> DomainMetricReport:
    """domains: parallel array of domain labels (e.g. "politifact"/
    "gossipcop") the same length as y_true/y_pred."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    domains = np.asarray(domains)
    y_score_arr = np.asarray(y_score) if y_score is not None else None

    if not (y_true.shape[0] == y_pred.shape[0] == domains.shape[0]):
        raise ValueError("y_true, y_pred, and domains must be the same length")

    per_domain: dict[str, MetricReport] = {}
    for domain in sorted(set(domains.tolist())):
        mask = domains == domain
        per_domain[domain] = compute_metrics(
            y_true[mask],
            y_pred[mask],
            y_score_arr[mask] if y_score_arr is not None else None,
        )

    aggregate = compute_metrics(y_true, y_pred, y_score_arr)
    return DomainMetricReport(per_domain=per_domain, aggregate=aggregate)
