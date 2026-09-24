"""
Calibration assessment (Phases.md Batch K): reliability diagram data,
Brier score, and temperature scaling. Determines whether
`is_calibrated_prob` can be `true` for a given model version
(Phases.md exit gate) — that verdict is a threshold judgment made by
the caller against `CalibrationReport`, not baked into this module.

Pure numpy/scipy — no torch dependency, so this is fully testable
here regardless of which model (baseline or GNN) produced the scores.
"""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize_scalar


@dataclass(frozen=True)
class ReliabilityBin:
    bin_lower: float
    bin_upper: float
    mean_predicted_prob: float | None  # None if bin is empty
    empirical_accuracy: float | None
    count: int


@dataclass(frozen=True)
class CalibrationReport:
    brier_score: float
    reliability_bins: list[ReliabilityBin]
    expected_calibration_error: float

    def as_dict(self) -> dict:
        return {
            "brier_score": self.brier_score,
            "expected_calibration_error": self.expected_calibration_error,
            "reliability_bins": [
                {
                    "bin_lower": b.bin_lower,
                    "bin_upper": b.bin_upper,
                    "mean_predicted_prob": b.mean_predicted_prob,
                    "empirical_accuracy": b.empirical_accuracy,
                    "count": b.count,
                }
                for b in self.reliability_bins
            ],
        }


def brier_score(y_true: np.ndarray | list[int], y_prob: np.ndarray | list[float]) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    if y_true.shape != y_prob.shape:
        raise ValueError(f"y_true shape {y_true.shape} != y_prob shape {y_prob.shape}")
    if y_true.shape[0] == 0:
        raise ValueError("Cannot compute Brier score on empty input")
    return float(np.mean((y_prob - y_true) ** 2))


def reliability_diagram(
    y_true: np.ndarray | list[int],
    y_prob: np.ndarray | list[float],
    *,
    n_bins: int = 10,
) -> list[ReliabilityBin]:
    """Bins predicted probabilities into `n_bins` equal-width buckets
    over [0, 1] and reports, per bucket, the mean predicted
    probability vs. the empirical fraction of positives — the
    standard reliability-diagram construction. Empty bins are
    reported (mean/accuracy = None, count = 0) rather than omitted,
    so a caller plotting this always gets exactly n_bins entries."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    if y_true.shape != y_prob.shape:
        raise ValueError(f"y_true shape {y_true.shape} != y_prob shape {y_prob.shape}")
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = []
    for i in range(n_bins):
        lower, upper = edges[i], edges[i + 1]
        # last bin is closed on both ends so p=1.0 falls into it
        if i == n_bins - 1:
            mask = (y_prob >= lower) & (y_prob <= upper)
        else:
            mask = (y_prob >= lower) & (y_prob < upper)
        count = int(mask.sum())
        if count == 0:
            bins.append(ReliabilityBin(float(lower), float(upper), None, None, 0))
        else:
            bins.append(
                ReliabilityBin(
                    float(lower),
                    float(upper),
                    float(y_prob[mask].mean()),
                    float(y_true[mask].mean()),
                    count,
                )
            )
    return bins


def expected_calibration_error(bins: list[ReliabilityBin], n_total: int) -> float:
    """Weighted average |confidence - accuracy| across non-empty bins,
    weighted by bin occupancy — the standard ECE definition."""
    if n_total <= 0:
        raise ValueError("n_total must be positive")
    ece = 0.0
    for b in bins:
        if b.count == 0:
            continue
        ece += (b.count / n_total) * abs(b.mean_predicted_prob - b.empirical_accuracy)
    return float(ece)


def assess_calibration(
    y_true: np.ndarray | list[int],
    y_prob: np.ndarray | list[float],
    *,
    n_bins: int = 10,
) -> CalibrationReport:
    y_true_arr = np.asarray(y_true, dtype=float)
    bins = reliability_diagram(y_true, y_prob, n_bins=n_bins)
    ece = expected_calibration_error(bins, n_total=y_true_arr.shape[0])
    return CalibrationReport(
        brier_score=brier_score(y_true, y_prob),
        reliability_bins=bins,
        expected_calibration_error=ece,
    )


def fit_temperature(
    y_true: np.ndarray | list[int],
    logits: np.ndarray | list[float],
) -> float:
    """Fits a single scalar temperature T > 0 minimizing NLL of
    sigmoid(logits / T) against y_true (Platt/temperature scaling for
    binary classification). Returns T; callers apply it as
    sigmoid(logits / T) to get calibrated probabilities. Only meant to
    be *fit* on a held-out validation set, never on the training or
    test split — that split discipline is the caller's
    responsibility, this function has no notion of which split it was
    given."""
    y_true = np.asarray(y_true, dtype=float)
    logits = np.asarray(logits, dtype=float)
    if y_true.shape != logits.shape:
        raise ValueError(f"y_true shape {y_true.shape} != logits shape {logits.shape}")
    if y_true.shape[0] == 0:
        raise ValueError("Cannot fit temperature on empty input")

    def nll(t: float) -> float:
        if t <= 0:
            return float("inf")
        p = 1.0 / (1.0 + np.exp(-logits / t))
        eps = 1e-12
        p = np.clip(p, eps, 1 - eps)
        return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))

    result = minimize_scalar(nll, bounds=(1e-3, 100.0), method="bounded")
    return float(result.x)
