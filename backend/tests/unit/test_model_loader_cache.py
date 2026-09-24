"""Tests for the model-artifact caching wrapper (app/ml_inference/model_loader.py::load_model_artifact_cached).

Deliberately decoupled from `load_model_artifact` itself (the real,
torch-dependent loader is exercised separately in
test_ml_inference.py, which requires torch/torch_geometric to run).
`model_loader.py`'s research-package imports are lazy -- confined to
inside `load_model_artifact`'s own body -- so importing this module at
all does not require torch, and these tests verify the caching logic
in complete isolation from it by monkeypatching the module-level
`load_model_artifact` name with a lightweight counting stub. This
makes cache hit/miss/version-safety behavior genuinely testable (and
tested, in CI and in any environment) even where torch is unavailable.
"""

from __future__ import annotations

from pathlib import Path

from app.ml_inference import model_loader


def _install_counting_stub(monkeypatch):
    calls = []

    def fake_load_model_artifact(*, checkpoint_dir, manifest_path, model_version, epoch=None):
        calls.append((checkpoint_dir, manifest_path, model_version, epoch))
        return object()  # fresh, distinct sentinel per real call

    monkeypatch.setattr(model_loader, "load_model_artifact", fake_load_model_artifact)
    model_loader._load_model_artifact_cached_impl.cache_clear()
    return calls


def test_cache_hit_returns_same_object_without_a_second_real_load(monkeypatch):
    calls = _install_counting_stub(monkeypatch)

    first = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/v1", manifest_path="/m/v1.json", model_version="v1"
    )
    second = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/v1", manifest_path="/m/v1.json", model_version="v1"
    )

    assert first is second
    assert len(calls) == 1


def test_cache_is_version_safe_a_different_model_version_never_returns_the_cached_model(monkeypatch):
    calls = _install_counting_stub(monkeypatch)

    v1 = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/v1", manifest_path="/m/v1.json", model_version="v1"
    )
    v2 = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/v1", manifest_path="/m/v1.json", model_version="v2"
    )

    assert v1 is not v2
    assert len(calls) == 2


def test_cache_is_safe_across_different_checkpoint_dirs_for_the_same_version(monkeypatch):
    calls = _install_counting_stub(monkeypatch)

    a = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/A", manifest_path="/m/v1.json", model_version="v1"
    )
    b = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/B", manifest_path="/m/v1.json", model_version="v1"
    )

    assert a is not b
    assert len(calls) == 2


def test_str_and_path_inputs_share_one_cache_entry(monkeypatch):
    calls = _install_counting_stub(monkeypatch)

    via_str = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/v1", manifest_path="/m/v1.json", model_version="v1"
    )
    via_path = model_loader.load_model_artifact_cached(
        checkpoint_dir=Path("/ckpt/v1"), manifest_path=Path("/m/v1.json"), model_version="v1"
    )

    assert via_str is via_path
    assert len(calls) == 1  # the Path-typed call must be a cache hit, not a second real load


def test_epoch_is_part_of_the_cache_key(monkeypatch):
    calls = _install_counting_stub(monkeypatch)

    latest = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/v1", manifest_path="/m/v1.json", model_version="v1", epoch=None
    )
    pinned = model_loader.load_model_artifact_cached(
        checkpoint_dir="/ckpt/v1", manifest_path="/m/v1.json", model_version="v1", epoch=5
    )

    assert latest is not pinned
    assert len(calls) == 2
