"""
Content encoder for the Text-Encoder+MLP baseline (Phases.md Batch J).

SCOPE, CORRECTED: this encoder is used ONLY by
models.baselines.TextEncoderMLPBaseline, which trains directly on raw
article text independent of UPFD's graph pipeline. It is NOT used to
construct GNN root-node features -- those come from UPFD's own native
per-feature-type vectors (see data/upfd_loader.py's module docstring
for why: UPFD's root and leaf nodes already share one encoder per
feature type, verified structurally from the loader's one-npz-per-
feature-type design). Re-encoding the root node with a separate
encoder would reintroduce the dimension mismatch this correction
resolved -- do not restore that behavior without re-deriving why it's
safe.

STATUS: sentence-transformers and torch ARE installed and importable
in this sandbox (confirmed by direct execution, not assumed) --
constructing ContentEncoder and calling encode() up through model
construction genuinely runs. What does NOT run here: downloading the
actual pretrained model weights, which requires reaching
huggingface.co -- confirmed unreachable via this sandbox's network
egress by actually attempting it and observing the OSError. So
`encode()`'s numerical output (the actual embeddings) remains
unverified here; the class's control flow up to that network call is
genuinely executed and tested.
"""
from dataclasses import dataclass

import numpy as np

DEFAULT_ENCODER_NAME = "all-MiniLM-L6-v2"


@dataclass
class ContentEncoder:
    """Wraps a frozen, pretrained sentence-transformers model
    (Batch I: no training-from-scratch, no full LLM fine-tuning).
    `encode()` returns a fixed-width embedding per input text, used as
    the input feature to TextEncoderMLPBaseline's MLP head."""

    model_name: str = DEFAULT_ENCODER_NAME
    _model: object = None  # lazily constructed on first encode() call

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required to use ContentEncoder "
                "and is not installed."
            ) from exc
        try:
            self._model = SentenceTransformer(self.model_name)
        except OSError as exc:
            # Observed directly in this sandbox: sentence-transformers
            # and torch import fine, but loading actual model weights
            # requires reaching huggingface.co, which this sandbox's
            # network egress does not allow -- confirmed by executing
            # this exact call and getting exactly this OSError, not
            # inferred from documentation.
            raise RuntimeError(
                f"Could not download model weights for {self.model_name!r} "
                f"(requires network access to huggingface.co). Verified "
                f"unreachable in this sandbox; should work in an environment "
                f"with normal internet access (e.g. Colab/Kaggle)."
            ) from exc

    def encode(self, texts: list[str]) -> np.ndarray:
        """Returns an (len(texts), embedding_dim) array. Raises
        ValueError on empty input rather than returning an empty
        array with an ambiguous shape."""
        if not texts:
            raise ValueError("Cannot encode an empty list of texts")
        self._ensure_loaded()
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings

    @property
    def embedding_dim(self) -> int:
        self._ensure_loaded()
        return self._model.get_sentence_embedding_dimension()
