"""
Config loading/validation for experiments/configs/*.yaml (Architecture.md
§9's layout: baseline_lr.yaml, baseline_rf.yaml, text_mlp.yaml,
dual_gnn.yaml, cross_domain.yaml). Pure Python/PyYAML -- no torch
dependency, fully testable here regardless of what's installed.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

VALID_MODEL_TYPES = ("baseline_lr", "baseline_rf", "text_mlp", "dual_gnn")
VALID_DATASETS = ("politifact", "gossipcop")
VALID_FEATURES = ("profile", "spacy", "bert", "content")

REQUIRED_TOP_LEVEL_KEYS = ("model_type", "dataset", "seed")


@dataclass(frozen=True)
class ExperimentConfig:
    model_type: str
    dataset: str
    seed: int
    feature: str = "bert"  # only meaningful for dual_gnn; see upfd_loader.py
    hyperparameters: dict = field(default_factory=dict)
    cross_domain_eval: bool = False
    checkpoint_dir: str = "model_checkpoints"
    output_dir: str = "evaluation"

    def __post_init__(self) -> None:
        if self.model_type not in VALID_MODEL_TYPES:
            raise ValueError(
                f"model_type must be one of {VALID_MODEL_TYPES}, got {self.model_type!r}"
            )
        if self.dataset not in VALID_DATASETS:
            raise ValueError(f"dataset must be one of {VALID_DATASETS}, got {self.dataset!r}")
        if self.feature not in VALID_FEATURES:
            raise ValueError(f"feature must be one of {VALID_FEATURES}, got {self.feature!r}")
        if not isinstance(self.seed, int):
            raise ValueError(f"seed must be an int, got {type(self.seed).__name__}")


def load_config(path: str | Path) -> ExperimentConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raise ValueError(f"Config file is empty: {path}")
    return parse_config_dict(raw)


def parse_config_dict(raw: dict) -> ExperimentConfig:
    missing = [k for k in REQUIRED_TOP_LEVEL_KEYS if k not in raw]
    if missing:
        raise ValueError(f"Config is missing required key(s): {missing}")

    known_fields = {
        "model_type", "dataset", "seed", "feature", "hyperparameters",
        "cross_domain_eval", "checkpoint_dir", "output_dir",
    }
    unknown = set(raw.keys()) - known_fields
    if unknown:
        raise ValueError(
            f"Config has unrecognized key(s): {sorted(unknown)} -- check for a "
            f"typo (e.g. did you mean 'hyperparameters'?)"
        )

    return ExperimentConfig(
        model_type=raw["model_type"],
        dataset=raw["dataset"],
        seed=raw["seed"],
        feature=raw.get("feature", "bert"),
        hyperparameters=raw.get("hyperparameters", {}),
        cross_domain_eval=raw.get("cross_domain_eval", False),
        checkpoint_dir=raw.get("checkpoint_dir", "model_checkpoints"),
        output_dir=raw.get("output_dir", "evaluation"),
    )
