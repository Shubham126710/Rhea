"""
ML Inference model loading -- Phases.md Phase 4, Architecture.md §2.

Reconstructs the DualLayerGNN architecture and loads real trained
weights from an artifact the research pipeline (research/) produced.
Deliberately imports the research package rather than duplicating the
model definition: Phase 4's own goal is "the Phase 3 artifact is
servable in production", which means reconstructing the EXACT
architecture Phase 3 trained, not a production-side reimplementation
that could silently drift from it. Architecture.md's overview
describes ML inference as an internal module of the same backend
service for v1 (a modular monolith, not microservices) -- this direct
import is how that's realized in code; it is not itself a locked
"Batch" decision and shouldn't be cited as one.

Checkpoint/manifest layout matches exactly what
research/experiments/run_experiment.py and
research/propagate_research/train/checkpointing.py actually write:
- checkpoints: <checkpoint_dir>/epoch_<N>.pt + epoch_<N>.json + latest.json
- manifest: a separate, caller-specified path (run_experiment.py uses
  different locations for its smoke-test vs. real-run paths, so this
  loader takes both paths explicitly rather than assuming one implies
  the other).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_RESEARCH_ROOT = Path(__file__).resolve().parents[3] / "research"
if str(_RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(_RESEARCH_ROOT))


@dataclass(frozen=True)
class LoadedModel:
    model: Any  # torch.nn.Module -- loosely typed so this dataclass is importable without torch
    model_version: str
    in_channels: int
    hidden_channels: int
    num_relations: int


def load_model_artifact(
    *,
    checkpoint_dir: str | Path,
    manifest_path: str | Path,
    model_version: str,
    epoch: int | None = None,
) -> LoadedModel:
    """`manifest_path` is the full path to a manifest.json file, i.e.
    exactly what packaging.save_manifest() returns -- this function
    passes its parent directory to packaging.load_manifest(), which
    expects a directory and appends "manifest.json" itself. Verifies
    the manifest's recorded model_version matches `model_version`
    EXACTLY (Rules.md §4: no implicit "latest" -- a caller asking for
    one version must never silently receive another), reconstructs
    DualLayerGNN from the manifest's own recorded config, and loads
    real weights from the checkpoint at `epoch` (or the latest
    completed epoch under `checkpoint_dir` if `epoch` is not given).
    """
    from propagate_research.artifacts.packaging import load_manifest
    from propagate_research.models.dual_layer_gnn import (
        DualLayerGNNConfig,
        build_dual_layer_gnn,
    )
    from propagate_research.train.checkpointing import CheckpointManager

    manifest = load_manifest(Path(manifest_path).parent)
    if manifest.model_version != model_version:
        raise ValueError(
            f"Requested model_version {model_version!r} does not match the "
            f"artifact's recorded model_version {manifest.model_version!r} "
            f"at {manifest_path}. Production never falls back to a "
            f"different version (Rules.md §4)."
        )

    in_channels = manifest.model_config.get("in_channels")
    if in_channels is None:
        raise ValueError(
            f"Artifact manifest at {manifest_path} has no in_channels "
            f"recorded in model_config -- cannot reconstruct the model."
        )

    gnn_config = DualLayerGNNConfig(
        in_channels=in_channels,
        hidden_channels=manifest.model_config.get("hidden_channels", 128),
        num_relations=manifest.model_config.get("num_relations", 2),
        dropout=manifest.model_config.get("dropout", 0.3),
    )
    model = build_dual_layer_gnn(gnn_config)

    mgr = CheckpointManager(checkpoint_dir=checkpoint_dir, run_id=model_version)
    target_epoch = epoch if epoch is not None else mgr.latest_epoch()
    if target_epoch is None:
        raise FileNotFoundError(
            f"No completed checkpoint found under {checkpoint_dir} "
            f"for model_version {model_version!r}."
        )
    state_blob, _meta = mgr.load(target_epoch)
    model.load_state_dict(state_blob["model_state"])
    model.eval()

    return LoadedModel(
        model=model,
        model_version=manifest.model_version,
        in_channels=in_channels,
        hidden_channels=gnn_config.hidden_channels,
        num_relations=gnn_config.num_relations,
    )


@lru_cache(maxsize=4)
def _load_model_artifact_cached_impl(
    *,
    checkpoint_dir: str,
    manifest_path: str,
    model_version: str,
    epoch: int | None = None,
) -> LoadedModel:
    return load_model_artifact(
        checkpoint_dir=checkpoint_dir,
        manifest_path=manifest_path,
        model_version=model_version,
        epoch=epoch,
    )


def load_model_artifact_cached(
    *,
    checkpoint_dir: str | Path,
    manifest_path: str | Path,
    model_version: str,
    epoch: int | None = None,
) -> LoadedModel:
    """Process-lifetime-cached wrapper around `load_model_artifact`.

    PERFORMANCE FIX: the analysis pipeline (`_run` in
    analysis_orchestration/pipeline.py) previously called
    `load_model_artifact` fresh on every single job -- reconstructing
    the DualLayerGNN, reading the checkpoint file, and calling
    `load_state_dict`/`.eval()` from disk each time, even though an RQ
    worker process handles many jobs over its lifetime and
    ACTIVE_MODEL_VERSION/the checkpoint directory don't change without
    a deploy + worker restart. That's redundant model loading on the
    hot path, not a one-time cost.

    This cache is scoped to the worker process's lifetime, exactly the
    same tradeoff `app.core.config.get_settings()` already makes with
    its own `lru_cache` in this codebase: config/model changes take
    effect on the next process restart, not instantly mid-process.
    That's a pre-existing, established pattern here, not a new one.

    Correctness note: `epoch=None` ("latest") is part of the cache key
    as literally passed, so if a caller relies on `epoch=None` picking
    up a checkpoint epoch added to disk *after* this process already
    cached a result for this exact (checkpoint_dir, manifest_path,
    model_version) combination, it won't see the new epoch until the
    worker restarts -- worker restart on deploy is the expected
    operational pattern here (see the get_settings() analogy above),
    not a regression this cache introduces. A different model_version
    (or different checkpoint_dir/manifest_path) is simply a different
    cache key and always loads its own real artifact -- the cache
    cannot return the wrong version for a given request.

    This thin function exists (rather than decorating the cache
    function directly with the public name) so `str | Path` inputs are
    normalized to `str` *before* the cache lookup happens -- `lru_cache`
    keys on the exact arguments it receives, so normalizing inside a
    cached function's own body would be too late to matter. A `Path`
    call and an equivalent `str` call (e.g. one from
    `app.core.config.Settings`, which declares these fields as plain
    `str`) are guaranteed to share one cache entry this way rather than
    silently creating two.
    """
    return _load_model_artifact_cached_impl(
        checkpoint_dir=str(checkpoint_dir),
        manifest_path=str(manifest_path),
        model_version=model_version,
        epoch=epoch,
    )
