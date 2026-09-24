"""
Model artifact packaging (Architecture.md §9 / Phases.md Batch T exit
gate): "a versioned model artifact exists with every field
Architecture.md §9 requires" -- checkpoint + preprocessing/model/
encoder config + model_version + dataset_version + git commit + seed.

This module only assembles and validates the *manifest* around a
checkpoint (whatever form the checkpoint file itself takes -- pickle
here, torch.save in the real training environment, per
train/checkpointing.py's note) -- it never inspects the checkpoint's
contents, so it has no torch dependency and is fully testable here.
"""
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ArtifactManifest:
    model_version: str
    dataset_version: str
    git_commit: str
    seed: int
    preprocessing_config: dict = field(default_factory=dict)
    model_config: dict = field(default_factory=dict)
    encoder_config: dict = field(default_factory=dict)
    checkpoint_filename: str = "model.pt"
    metrics_summary: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


REQUIRED_FIELDS = (
    "model_version",
    "dataset_version",
    "git_commit",
    "seed",
    "preprocessing_config",
    "model_config",
    "encoder_config",
)


def get_git_commit(repo_dir: str | Path = ".") -> str:
    """Returns the current commit hash of `repo_dir`, or raises
    RuntimeError with a clear message if it can't be determined (e.g.
    not a git checkout) -- an artifact silently shipped without a real
    commit hash would defeat the whole point of recording one."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            f"Could not determine git commit hash in {repo_dir!r}: {exc}. "
            f"A model artifact must not be packaged without one (Architecture.md §9)."
        ) from exc
    return result.stdout.strip()


def build_manifest(
    *,
    model_version: str,
    dataset_version: str,
    git_commit: str,
    seed: int,
    preprocessing_config: dict,
    model_config: dict,
    encoder_config: dict,
    checkpoint_filename: str = "model.pt",
    metrics_summary: dict | None = None,
) -> ArtifactManifest:
    if not model_version:
        raise ValueError("model_version is required and cannot be empty")
    if not dataset_version:
        raise ValueError("dataset_version is required and cannot be empty")
    if not git_commit:
        raise ValueError("git_commit is required and cannot be empty")
    return ArtifactManifest(
        model_version=model_version,
        dataset_version=dataset_version,
        git_commit=git_commit,
        seed=seed,
        preprocessing_config=preprocessing_config,
        model_config=model_config,
        encoder_config=encoder_config,
        checkpoint_filename=checkpoint_filename,
        metrics_summary=metrics_summary or {},
    )


def save_manifest(manifest: ArtifactManifest, artifact_dir: str | Path) -> Path:
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = artifact_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest.as_dict(), f, indent=2)
    return manifest_path


def load_manifest(artifact_dir: str | Path) -> ArtifactManifest:
    manifest_path = Path(artifact_dir) / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json found in {artifact_dir}")
    with open(manifest_path) as f:
        data = json.load(f)
    validate_manifest_dict(data)
    return ArtifactManifest(**data)


def validate_manifest_dict(data: dict) -> None:
    """Raises ValueError naming every missing field at once (not just
    the first) -- more useful when debugging a broken packaging run."""
    missing = [field_name for field_name in REQUIRED_FIELDS if field_name not in data]
    if missing:
        raise ValueError(f"Artifact manifest is missing required field(s): {missing}")
