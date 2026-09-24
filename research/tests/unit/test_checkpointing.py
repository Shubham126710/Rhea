import pickle

import pytest
from propagate_research.train.checkpointing import CheckpointManager


class _MockStatefulComponent:
    """A minimal stand-in for a torch.nn.Module or torch.optim.Optimizer
    satisfying the state_dict()/load_state_dict() protocol. This is
    NOT a model — it exists purely to validate that CheckpointManager's
    save/load/resume mechanics behave correctly, independent of any
    deep-learning framework. Model correctness is out of scope here
    (and out of scope for this whole sandbox — see Phase 3 report)."""

    def __init__(self, value: int = 0):
        self.value = value

    def state_dict(self):
        return {"value": self.value}

    def load_state_dict(self, state):
        self.value = state["value"]


def test_save_creates_state_and_metadata_files(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    model = _MockStatefulComponent(value=42)
    optimizer = _MockStatefulComponent(value=7)

    mgr.save(epoch=1, model=model, optimizer=optimizer, metrics={"loss": 0.5})

    assert (tmp_path / "epoch_1.pt").exists()
    assert (tmp_path / "epoch_1.json").exists()
    assert (tmp_path / "latest.json").exists()


def test_load_round_trips_state_exactly(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    model = _MockStatefulComponent(value=123)
    optimizer = _MockStatefulComponent(value=456)
    mgr.save(epoch=3, model=model, optimizer=optimizer, metrics={"loss": 0.1, "acc": 0.9})

    state_blob, metadata = mgr.load(3)

    assert state_blob["model_state"] == {"value": 123}
    assert state_blob["optimizer_state"] == {"value": 456}
    assert metadata.epoch == 3
    assert metadata.run_id == "run-1"
    assert metadata.metrics == {"loss": 0.1, "acc": 0.9}


def test_latest_epoch_none_for_fresh_run(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    assert mgr.latest_epoch() is None


def test_latest_epoch_tracks_most_recent_save(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    model, optimizer = _MockStatefulComponent(), _MockStatefulComponent()

    mgr.save(epoch=1, model=model, optimizer=optimizer, metrics={})
    assert mgr.latest_epoch() == 1
    mgr.save(epoch=2, model=model, optimizer=optimizer, metrics={})
    assert mgr.latest_epoch() == 2
    # out-of-order save still updates "latest" to whatever was saved
    # last, which is the correct behavior for resume: resume always
    # continues from the most recently completed save.
    mgr.save(epoch=1, model=model, optimizer=optimizer, metrics={})
    assert mgr.latest_epoch() == 1


def test_resume_restores_model_and_optimizer_in_place(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    training_model = _MockStatefulComponent(value=99)
    training_optimizer = _MockStatefulComponent(value=11)
    mgr.save(epoch=5, model=training_model, optimizer=training_optimizer, metrics={"loss": 0.2})

    fresh_model = _MockStatefulComponent(value=0)
    fresh_optimizer = _MockStatefulComponent(value=0)
    metadata = mgr.resume(model=fresh_model, optimizer=fresh_optimizer)

    assert metadata is not None
    assert metadata.epoch == 5
    assert fresh_model.value == 99
    assert fresh_optimizer.value == 11


def test_resume_on_fresh_run_returns_none_and_leaves_state_untouched():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        mgr = CheckpointManager(d, run_id="run-1")
        model = _MockStatefulComponent(value=1)
        optimizer = _MockStatefulComponent(value=2)
        result = mgr.resume(model=model, optimizer=optimizer)
        assert result is None
        assert model.value == 1  # untouched
        assert optimizer.value == 2  # untouched


def test_load_missing_epoch_raises(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    with pytest.raises(FileNotFoundError):
        mgr.load(99)


def test_multiple_epochs_each_independently_loadable(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    for epoch in range(3):
        model = _MockStatefulComponent(value=epoch * 10)
        optimizer = _MockStatefulComponent(value=epoch)
        mgr.save(epoch=epoch, model=model, optimizer=optimizer, metrics={"epoch": epoch})

    for epoch in range(3):
        state_blob, metadata = mgr.load(epoch)
        assert state_blob["model_state"] == {"value": epoch * 10}
        assert metadata.epoch == epoch


def test_save_does_not_leave_tmp_files_behind(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    model, optimizer = _MockStatefulComponent(), _MockStatefulComponent()
    mgr.save(epoch=1, model=model, optimizer=optimizer, metrics={})

    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []


def test_metadata_includes_timestamp_and_extra_fields(tmp_path):
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    model, optimizer = _MockStatefulComponent(), _MockStatefulComponent()
    metadata = mgr.save(
        epoch=1,
        model=model,
        optimizer=optimizer,
        metrics={"loss": 0.3},
        extra={"lr": 0.001, "seed": 42},
    )
    assert metadata.saved_at_unix > 0
    assert metadata.extra == {"lr": 0.001, "seed": 42}


def test_checkpoint_dir_created_if_missing(tmp_path):
    nested = tmp_path / "does" / "not" / "exist" / "yet"
    CheckpointManager(nested, run_id="run-1")
    assert nested.exists()


def test_state_blob_is_pickle_not_torch_specific(tmp_path):
    """Confirms the state format has no torch dependency baked in --
    a plain pickle load (no torch import) can read it back."""
    mgr = CheckpointManager(tmp_path, run_id="run-1")
    model, optimizer = _MockStatefulComponent(value=5), _MockStatefulComponent(value=6)
    mgr.save(epoch=1, model=model, optimizer=optimizer, metrics={})

    with open(tmp_path / "epoch_1.pt", "rb") as f:
        raw = pickle.load(f)
    assert raw == {"model_state": {"value": 5}, "optimizer_state": {"value": 6}}


# --- executed for real against an actual torch model (torch IS
# installed in this sandbox) -- this is the one place checkpointing
# is verified against real tensors, not just the mock protocol above ---


def test_checkpoint_resume_works_with_real_torch_model_and_optimizer(tmp_path):
    torch = pytest.importorskip("torch")
    import torch.nn as nn

    model = nn.Linear(4, 2)
    optimizer = torch.optim.Adam(model.parameters())
    mgr = CheckpointManager(tmp_path, run_id="real-torch-test")
    mgr.save(epoch=3, model=model, optimizer=optimizer, metrics={"loss": 0.42})

    fresh_model = nn.Linear(4, 2)
    fresh_optimizer = torch.optim.Adam(fresh_model.parameters())
    metadata = mgr.resume(model=fresh_model, optimizer=fresh_optimizer)

    assert metadata is not None
    assert metadata.epoch == 3
    assert torch.equal(model.weight, fresh_model.weight)
    assert torch.equal(model.bias, fresh_model.bias)
