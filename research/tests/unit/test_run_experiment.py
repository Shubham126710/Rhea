import json
import subprocess
import sys
from pathlib import Path

import pytest

RESEARCH_ROOT = Path(__file__).parent.parent.parent
RUN_EXPERIMENT = RESEARCH_ROOT / "experiments" / "run_experiment.py"
CONFIGS_DIR = RESEARCH_ROOT / "experiments" / "configs"


def _run(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUN_EXPERIMENT)] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,  # None (default) preserves subprocess.run's own behavior: inherit os.environ
    )


def test_dry_run_baseline_lr_config():
    args = ["--config", str(CONFIGS_DIR / "baseline_lr.yaml"), "--dry-run"]
    result = _run(args, cwd=RESEARCH_ROOT)
    assert result.returncode == 0
    assert "model_type: baseline_lr" in result.stdout


def test_dry_run_dual_gnn_config():
    result = _run(["--config", str(CONFIGS_DIR / "dual_gnn.yaml"), "--dry-run"], cwd=RESEARCH_ROOT)
    assert result.returncode == 0
    assert "model_type: dual_gnn" in result.stdout


def test_dry_run_missing_config_fails_cleanly():
    result = _run(["--config", "/nonexistent/config.yaml", "--dry-run"], cwd=RESEARCH_ROOT)
    assert result.returncode != 0


def test_smoke_test_baseline_lr_runs_end_to_end(tmp_path):
    result = _run(
        ["--config", str(CONFIGS_DIR / "baseline_lr.yaml"), "--smoke-test"],
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "Smoke test metrics" in result.stdout
    assert "accuracy" in result.stdout


def test_smoke_test_baseline_rf_runs_end_to_end(tmp_path):
    result = _run(
        ["--config", str(CONFIGS_DIR / "baseline_rf.yaml"), "--smoke-test"],
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "Smoke test metrics" in result.stdout


def test_smoke_test_writes_real_artifact_manifest_when_in_git_repo(tmp_path):
    """Manifest writing depends on get_git_commit() succeeding
    (artifacts/packaging.py refuses to fabricate a commit hash). This
    project has no .git directory in this sandbox (confirmed
    elsewhere -- see test_packaging.py's identical conditional), so
    this test checks whichever behavior is actually correct for the
    environment it's running in, rather than assuming one."""
    try:
        is_git_repo = (
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=RESEARCH_ROOT.parent,  # matches what run_experiment.py itself checks
                capture_output=True,
            ).returncode
            == 0
        )
    except (FileNotFoundError, OSError):
        is_git_repo = False  # git itself not invokable in this environment

    result = _run(
        ["--config", str(CONFIGS_DIR / "baseline_lr.yaml"), "--smoke-test"],
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    manifest_path = tmp_path / "model_checkpoints" / "baseline_lr" / "smoketest" / "manifest.json"

    if is_git_repo:
        assert manifest_path.exists()
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["model_version"] == "baseline_lr-smoketest"
        assert "git_commit" in manifest
        assert manifest["seed"] == 42
    else:
        assert not manifest_path.exists()
        assert "artifact packaging skipped" in result.stderr


def test_smoke_test_handles_yaml_list_ngram_range_correctly():
    """Regression test: YAML has no tuple type, so ngram_range loads as
    a list ([1, 2]) -- sklearn's TfidfVectorizer requires a tuple and
    raises InvalidParameterError otherwise. This caught a real bug in
    _build_baseline() the first time this test ran."""
    import yaml as yaml_module

    config_dict = yaml_module.safe_load((CONFIGS_DIR / "baseline_lr.yaml").read_text())
    # confirms the YAML shape
    assert isinstance(config_dict["hyperparameters"]["ngram_range"], list)

    # if _build_baseline didn't convert list->tuple, this smoke test
    # would fail with InvalidParameterError, same as it did pre-fix
    result = _run(
        ["--config", str(CONFIGS_DIR / "baseline_lr.yaml"), "--smoke-test"],
        cwd=CONFIGS_DIR,
    )
    assert result.returncode == 0, result.stderr


def test_smoke_test_rejects_dual_gnn_via_this_cli():
    result = _run(
        ["--config", str(CONFIGS_DIR / "dual_gnn.yaml"), "--smoke-test"],
        cwd=RESEARCH_ROOT,
    )
    assert result.returncode != 0
    assert "own test suite" in result.stderr


def test_smoke_test_text_mlp_reaches_real_encoder_and_fails_at_network_boundary(tmp_path):
    """text_mlp's smoke-test dispatch is real (unlike dual_gnn, which
    is deliberately excluded from this CLI path) -- it reaches the
    real ContentEncoder.encode() call. This subprocess test forces a
    deterministic, network-independent failure there via standard
    Hugging Face offline-mode env vars (HF_HUB_OFFLINE + an empty,
    guaranteed-uncached HF_HOME) rather than relying on this sandbox's
    incidental network block, which silently stopped being true the
    moment a real cache or real network access was available (found
    when this same test passed 202/202 in one environment and failed
    in another that had cached weights). The encoder call itself is
    still real and unmocked; only its ability to reach the network or
    an existing cache is removed.

    DETERMINISTIC TEST SEAM: this specifically requires
    sentence_transformers to be importable in the SAME interpreter the
    subprocess launches under (sys.executable) -- without it, the
    subprocess fails earlier with ModuleNotFoundError instead of
    reaching the network-boundary error this test checks for, which
    is a different, unrelated failure this test was never meant to
    assert on. Skipping (not weakening the assertion) is the correct
    signal in an environment that lacks the dependency outright.
    """
    pytest.importorskip("sentence_transformers")
    import os

    empty_cache_dir = tmp_path / "empty_hf_cache"
    empty_cache_dir.mkdir()
    env = {
        **os.environ,
        "HF_HUB_OFFLINE": "1",
        "HF_HOME": str(empty_cache_dir),
        "TRANSFORMERS_CACHE": str(empty_cache_dir),
    }
    result = _run(
        ["--config", str(CONFIGS_DIR / "text_mlp.yaml"), "--smoke-test"],
        cwd=RESEARCH_ROOT,
        env=env,
    )
    assert result.returncode != 0
    assert "huggingface" in result.stderr.lower() or "huggingface" in result.stdout.lower()


def test_full_run_without_dry_run_or_smoke_test_explains_network_limitation():
    result = _run(["--config", str(CONFIGS_DIR / "baseline_lr.yaml")], cwd=RESEARCH_ROOT)
    assert result.returncode != 0
    assert "network-blocked" in result.stderr


# --- cross-domain dispatch ---


def test_cross_domain_config_dispatches_to_cross_domain_path_not_ordinary_training(tmp_path):
    """Proves the dispatch actually performs cross-domain evaluation
    rather than merely parsing the flag: the traceback must show
    _run_cross_domain -> _train_dual_gnn was entered, not the ordinary
    single-domain _run_dual_gnn path.

    This is a subprocess test, so in-process mocking can't reach it.
    Forces a fast, deterministic, network-independent failure by
    pointing PROPAGATE_UPFD_ROOT at a path that is a plain FILE, not a
    directory -- UPFD's loader fails immediately trying to create a
    subdirectory under it, regardless of whether real UPFD data is
    cached or downloadable elsewhere on the machine running this test.
    Found necessary because real UPFD access being genuinely available
    in some environments (the whole point of this project's earlier
    verification work) meant this test could previously fall through
    into actually running real training as an unintended side effect
    of a dispatch-reachability check, risking a 120s timeout or worse.
    The assertions below only check which function appears in the
    traceback, not why it failed, so this substitution doesn't change
    what the test proves."""
    import os

    bogus_root = tmp_path / "not_a_directory"
    bogus_root.write_text("")  # a file, not a dir -- guarantees fast OSError
    env = {**os.environ, "PROPAGATE_UPFD_ROOT": str(bogus_root)}

    result = _run(
        ["--config", str(CONFIGS_DIR / "cross_domain.yaml")], cwd=RESEARCH_ROOT, env=env
    )
    assert result.returncode != 0
    assert "_run_cross_domain" in result.stderr
    assert "_run_dual_gnn(config)" not in result.stderr  # not the single-domain path


def test_cross_domain_eval_flag_on_non_gnn_model_type_fails_clearly(tmp_path):
    """Invalid combination: cross_domain_eval=True with a baseline
    model_type must fail with a clear message, not silently run an
    ordinary baseline experiment as if the flag had no effect."""
    import yaml

    bad_config = tmp_path / "bad_cross_domain.yaml"
    bad_config.write_text(
        yaml.dump(
            {
                "model_type": "baseline_lr",
                "dataset": "politifact",
                "seed": 42,
                "cross_domain_eval": True,
            }
        )
    )
    result = _run(["--config", str(bad_config)], cwd=RESEARCH_ROOT)
    assert result.returncode != 0
    assert "only meaningful for model_type='dual_gnn'" in result.stderr


def test_cross_domain_config_dry_run_shows_flag_set():
    result = _run(
        ["--config", str(CONFIGS_DIR / "cross_domain.yaml"), "--dry-run"], cwd=RESEARCH_ROOT
    )
    assert result.returncode == 0
    assert "cross_domain_eval: True" in result.stdout


# --- ablation dispatch ---


def test_ablation_hyperparameter_reaches_apply_ablation(tmp_path):
    """Proves an ablation-configured run actually reaches
    apply_ablation() in the real data-loading path, not just that the
    config value is accepted and ignored.

    Same subprocess-mocking limitation and fix as the cross-domain
    dispatch test above: PROPAGATE_UPFD_ROOT points at a file, not a
    directory, forcing a fast, deterministic, network-independent
    failure inside _load_relation_graphs rather than depending on
    UPFD being genuinely unreachable, which is no longer reliably true
    in every environment this test might run in.

    DETERMINISTIC TEST SEAM: dual_gnn's data-loading path imports
    torch/torch_geometric before it can reach _load_relation_graphs at
    all -- without them, the subprocess fails at that import instead,
    with a traceback that never mentions _load_relation_graphs, which
    is a different, unrelated failure this test was never meant to
    assert on. Skipping (not weakening the assertion) is the correct
    signal in an environment that lacks the dependency outright.
    """
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    import os

    import yaml

    upfd_root = tmp_path / "not_a_directory"
    upfd_root.write_text("")
    env = {**os.environ, "PROPAGATE_UPFD_ROOT": str(upfd_root)}

    ablation_config = tmp_path / "ablation_dual_gnn.yaml"
    ablation_config.write_text(
        yaml.dump(
            {
                "model_type": "dual_gnn",
                "dataset": "politifact",
                "feature": "bert",
                "seed": 42,
                "hyperparameters": {"ablation": "propagation_only", "epochs": 3},
            }
        )
    )
    result = _run(["--config", str(ablation_config)], cwd=RESEARCH_ROOT, env=env)
    assert result.returncode != 0
    # reaches the real loader call, inside _load_relation_graphs, which
    # is the function that calls apply_ablation() -- confirms the
    # ablation-aware code path was entered, not skipped
    assert "_load_relation_graphs" in result.stderr
