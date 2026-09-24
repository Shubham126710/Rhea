from pathlib import Path

import pytest
from propagate_research.artifacts.packaging import (
    REQUIRED_FIELDS,
    build_manifest,
    get_git_commit,
    load_manifest,
    save_manifest,
    validate_manifest_dict,
)


def _sample_manifest():
    return build_manifest(
        model_version="dualgnn-v1.0.0",
        dataset_version="upfd-politifact-2021",
        git_commit="abc123",
        seed=42,
        preprocessing_config={"normalization_version": "1.0.0"},
        model_config={"hidden_dim": 128, "relations": ["direct_share", "inherited_share"]},
        encoder_config={"name": "all-MiniLM-L6-v2"},
    )


def test_build_manifest_has_all_required_fields():
    manifest = _sample_manifest()
    d = manifest.as_dict()
    for f in REQUIRED_FIELDS:
        assert f in d


def test_build_manifest_rejects_empty_model_version():
    with pytest.raises(ValueError):
        build_manifest(
            model_version="",
            dataset_version="d",
            git_commit="c",
            seed=1,
            preprocessing_config={},
            model_config={},
            encoder_config={},
        )


def test_build_manifest_rejects_empty_dataset_version():
    with pytest.raises(ValueError):
        build_manifest(
            model_version="m",
            dataset_version="",
            git_commit="c",
            seed=1,
            preprocessing_config={},
            model_config={},
            encoder_config={},
        )


def test_build_manifest_rejects_empty_git_commit():
    with pytest.raises(ValueError):
        build_manifest(
            model_version="m",
            dataset_version="d",
            git_commit="",
            seed=1,
            preprocessing_config={},
            model_config={},
            encoder_config={},
        )


def test_save_and_load_manifest_round_trips(tmp_path):
    manifest = _sample_manifest()
    save_manifest(manifest, tmp_path)
    loaded = load_manifest(tmp_path)
    assert loaded == manifest


def test_save_manifest_creates_directory_if_missing(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    manifest = _sample_manifest()
    save_manifest(manifest, nested)
    assert (nested / "manifest.json").exists()


def test_load_manifest_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path)


def test_validate_manifest_dict_reports_all_missing_fields():
    with pytest.raises(ValueError) as exc_info:
        validate_manifest_dict({"model_version": "v1"})
    message = str(exc_info.value)
    for f in REQUIRED_FIELDS:
        if f != "model_version":
            assert f in message


def test_validate_manifest_dict_passes_for_complete_dict():
    d = _sample_manifest().as_dict()
    validate_manifest_dict(d)  # should not raise


def test_get_git_commit_works_in_this_repo():
    # Must check the SAME directory production code targets, not an
    # arbitrary "." (pytest's invocation cwd, which is environment-
    # dependent and was found to diverge from what run_experiment.py
    # actually passes to get_git_commit: Path(__file__).parent.parent.parent
    # from experiments/run_experiment.py, i.e. the repo root -- not
    # wherever pytest happened to be invoked from). Mismatched targets
    # made this test's result depend on the caller's cwd rather than on
    # get_git_commit()'s actual behavior.
    import subprocess

    repo_root = Path(__file__).parent.parent.parent.parent
    try:
        is_git_repo = (
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=repo_root,
                capture_output=True,
            ).returncode
            == 0
        )
    except (FileNotFoundError, OSError):
        is_git_repo = False  # git itself not invokable in this environment

    if is_git_repo:
        commit = get_git_commit(str(repo_root))
        assert isinstance(commit, str) and len(commit) > 0
    else:
        with pytest.raises(RuntimeError):
            get_git_commit(str(repo_root))


def test_get_git_commit_raises_for_non_git_directory(tmp_path):
    with pytest.raises(RuntimeError):
        get_git_commit(tmp_path)
