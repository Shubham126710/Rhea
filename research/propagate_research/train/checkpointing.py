"""
Checkpoint save/load/resume mechanics for Decision 4 (Colab/Kaggle are
non-persistent, session-limited — a disconnect or timeout must not
lose a training run).

Deliberately framework-agnostic: this module never imports torch. It
operates on anything with a `.state_dict()` / `.load_state_dict()`
pair (torch modules and torch optimizers both satisfy this duck-typed
protocol, but so does a plain test double) — that's what makes the
checkpoint/resume *infrastructure* unit-testable in an environment
with no torch installed, as distinct from testing model correctness,
which this module makes no claims about.

Design: every checkpoint directory is config-driven (a plain path
string), so the identical code points at a local folder here, a
Drive-mounted path on Colab, or /kaggle/working/ on Kaggle — no
environment branching in this module or its caller.
"""
import json
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class _StatefulComponent(Protocol):
    def state_dict(self) -> dict[str, Any]: ...
    def load_state_dict(self, state: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class CheckpointMetadata:
    epoch: int
    run_id: str
    metrics: dict[str, float]
    saved_at_unix: float
    extra: dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """One instance per training run. `checkpoint_dir` is created if
    it doesn't exist. Every save writes two files: `epoch_<N>.pt`
    (model + optimizer state via pickle — swap for torch.save in the
    real training environment, see note below) and a matching
    `epoch_<N>.json` (human-readable metadata: epoch, metrics, run_id,
    timestamp) so a run's progress can be inspected without
    unpickling anything. `latest.json` always points at the most
    recent successful save, so resume doesn't need to scan the
    directory.

    Note on serialization: this class uses pickle for the state blob
    so it has zero framework dependency and is fully testable here.
    The real training environment (Colab/Kaggle, with torch installed)
    should subclass or configure this with torch.save/torch.load for
    the state blob instead of pickle, for the usual reasons (pickle
    is not a safe/portable format for tensors across torch versions/
    devices) — the directory layout, metadata schema, and resume
    logic below do not change either way.
    """

    def __init__(self, checkpoint_dir: str | Path, run_id: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id

    def _state_path(self, epoch: int) -> Path:
        return self.checkpoint_dir / f"epoch_{epoch}.pt"

    def _meta_path(self, epoch: int) -> Path:
        return self.checkpoint_dir / f"epoch_{epoch}.json"

    @property
    def _latest_pointer_path(self) -> Path:
        return self.checkpoint_dir / "latest.json"

    def save(
        self,
        *,
        epoch: int,
        model: _StatefulComponent,
        optimizer: _StatefulComponent,
        metrics: dict[str, float],
        extra: dict[str, Any] | None = None,
    ) -> CheckpointMetadata:
        """Writes the state blob and metadata, then atomically updates
        the `latest.json` pointer last — so a crash mid-save never
        leaves `latest.json` pointing at a partially-written
        checkpoint. This is the specific mechanism that makes
        mid-training disconnects safe to resume from."""
        state_blob = {
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
        }
        state_path = self._state_path(epoch)
        tmp_state_path = state_path.with_suffix(".pt.tmp")
        with open(tmp_state_path, "wb") as f:
            pickle.dump(state_blob, f)
        tmp_state_path.replace(state_path)  # atomic on POSIX

        metadata = CheckpointMetadata(
            epoch=epoch,
            run_id=self.run_id,
            metrics=metrics,
            saved_at_unix=time.time(),
            extra=extra or {},
        )
        meta_path = self._meta_path(epoch)
        tmp_meta_path = meta_path.with_suffix(".json.tmp")
        with open(tmp_meta_path, "w") as f:
            json.dump(_metadata_to_dict(metadata), f, indent=2)
        tmp_meta_path.replace(meta_path)

        # Update the "latest" pointer last, and atomically, so it
        # never references a checkpoint whose files aren't fully
        # written yet.
        tmp_latest = self._latest_pointer_path.with_suffix(".json.tmp")
        with open(tmp_latest, "w") as f:
            json.dump({"epoch": epoch}, f)
        tmp_latest.replace(self._latest_pointer_path)

        return metadata

    def load(self, epoch: int) -> tuple[dict[str, Any], CheckpointMetadata]:
        state_path = self._state_path(epoch)
        meta_path = self._meta_path(epoch)
        if not state_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"No complete checkpoint found for epoch {epoch} in {self.checkpoint_dir}"
            )
        with open(state_path, "rb") as f:
            state_blob = pickle.load(f)
        with open(meta_path) as f:
            meta_dict = json.load(f)
        return state_blob, _metadata_from_dict(meta_dict)

    def latest_epoch(self) -> int | None:
        """Returns the epoch number to resume from, or None if this
        run has no completed checkpoint yet (a fresh start, not an
        error)."""
        if not self._latest_pointer_path.exists():
            return None
        with open(self._latest_pointer_path) as f:
            return json.load(f)["epoch"]

    def resume(
        self, *, model: _StatefulComponent, optimizer: _StatefulComponent
    ) -> CheckpointMetadata | None:
        """Loads the latest checkpoint into `model`/`optimizer` in
        place and returns its metadata, or returns None (leaving
        model/optimizer untouched) if there's nothing to resume from.
        Callers should treat a None return as "start from epoch 0",
        not as an error."""
        epoch = self.latest_epoch()
        if epoch is None:
            return None
        state_blob, metadata = self.load(epoch)
        model.load_state_dict(state_blob["model_state"])
        optimizer.load_state_dict(state_blob["optimizer_state"])
        return metadata


def _metadata_to_dict(metadata: CheckpointMetadata) -> dict[str, Any]:
    return {
        "epoch": metadata.epoch,
        "run_id": metadata.run_id,
        "metrics": metadata.metrics,
        "saved_at_unix": metadata.saved_at_unix,
        "extra": metadata.extra,
    }


def _metadata_from_dict(data: dict[str, Any]) -> CheckpointMetadata:
    return CheckpointMetadata(
        epoch=data["epoch"],
        run_id=data["run_id"],
        metrics=data["metrics"],
        saved_at_unix=data["saved_at_unix"],
        extra=data.get("extra", {}),
    )
