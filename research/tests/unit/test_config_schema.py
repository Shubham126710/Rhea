from pathlib import Path

import pytest
import yaml
from propagate_research.config.schema import (
    VALID_DATASETS,
    VALID_FEATURES,
    VALID_MODEL_TYPES,
    ExperimentConfig,
    load_config,
    parse_config_dict,
)

CONFIGS_DIR = Path(__file__).parent.parent.parent / "experiments" / "configs"


def test_parse_minimal_valid_config():
    config = parse_config_dict({"model_type": "baseline_lr", "dataset": "politifact", "seed": 1})
    assert config.model_type == "baseline_lr"
    assert config.feature == "bert"  # default


def test_parse_rejects_missing_required_keys():
    with pytest.raises(ValueError):
        parse_config_dict({"model_type": "baseline_lr"})


def test_parse_rejects_unknown_keys():
    with pytest.raises(ValueError):
        parse_config_dict(
            {"model_type": "baseline_lr", "dataset": "politifact", "seed": 1, "typo_field": 1}
        )


def test_config_rejects_invalid_model_type():
    with pytest.raises(ValueError):
        ExperimentConfig(model_type="not_a_model", dataset="politifact", seed=1)


def test_config_rejects_invalid_dataset():
    with pytest.raises(ValueError):
        ExperimentConfig(model_type="baseline_lr", dataset="not_a_dataset", seed=1)


def test_config_rejects_invalid_feature():
    with pytest.raises(ValueError):
        ExperimentConfig(model_type="dual_gnn", dataset="politifact", seed=1, feature="not_real")


def test_config_rejects_non_int_seed():
    with pytest.raises(ValueError):
        ExperimentConfig(model_type="baseline_lr", dataset="politifact", seed="42")  # type: ignore[arg-type]


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_load_config_empty_file_raises(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    with pytest.raises(ValueError):
        load_config(path)


def test_load_config_round_trip(tmp_path):
    path = tmp_path / "test_config.yaml"
    path.write_text(
        yaml.dump(
            {
                "model_type": "dual_gnn",
                "dataset": "gossipcop",
                "seed": 7,
                "feature": "spacy",
                "hyperparameters": {"hidden_channels": 64},
            }
        )
    )
    config = load_config(path)
    assert config.model_type == "dual_gnn"
    assert config.dataset == "gossipcop"
    assert config.seed == 7
    assert config.feature == "spacy"
    assert config.hyperparameters == {"hidden_channels": 64}


# --- against the real committed configs (Architecture.md §9's exact list) ---


@pytest.mark.parametrize(
    "filename",
    ["baseline_lr.yaml", "baseline_rf.yaml", "text_mlp.yaml", "dual_gnn.yaml", "cross_domain.yaml"],
)
def test_all_committed_configs_are_valid(filename):
    config = load_config(CONFIGS_DIR / filename)
    assert config.model_type in VALID_MODEL_TYPES
    assert config.dataset in VALID_DATASETS
    assert config.feature in VALID_FEATURES


def test_all_seven_architecture_configs_present():
    expected = {
        "baseline_lr.yaml", "baseline_rf.yaml", "text_mlp.yaml",
        "dual_gnn.yaml", "cross_domain.yaml",
        # Added when the ablation study's two variants (already
        # supported by build_graph.py's apply_ablation(), dispatched
        # via hyperparameters.ablation in run_experiment.py) were
        # materialized as their own runnable configs.
        "propagation_only.yaml", "interaction_only.yaml",
    }
    actual = {p.name for p in CONFIGS_DIR.glob("*.yaml")}
    assert expected == actual


def test_cross_domain_config_has_flag_set():
    config = load_config(CONFIGS_DIR / "cross_domain.yaml")
    assert config.cross_domain_eval is True


def test_baseline_configs_do_not_set_cross_domain():
    config = load_config(CONFIGS_DIR / "baseline_lr.yaml")
    assert config.cross_domain_eval is False
