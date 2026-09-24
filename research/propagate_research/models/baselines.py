"""
Baseline models (Phases.md Batch J): TF-IDF+LR, TF-IDF+RF,
Text-Encoder+MLP. All three are content-only (no graph input), so
they don't depend on the dataset fork/graph decisions at all.

TF-IDF+LR and TF-IDF+RF need only scikit-learn and are fully real,
executable, and unit-tested in this sandbox.

TextEncoderMLPBaseline is written to the same interface but depends on
`sentence-transformers` + `torch` for its encoder step, neither of
which could be installed in this sandbox (see the Phase 3 report for
why). Its code is complete and reviewed, but it has NOT been executed
here — do not treat it as verified the way the two sklearn baselines
are. It should be exercised for real the first time this pipeline
runs somewhere with those packages installed (Colab/Kaggle, per
Decision 4), before being relied on.
"""
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from propagate_research.encoders.content_encoder import ContentEncoder


class ContentBaseline(Protocol):
    """Common interface every content-only baseline satisfies, so the
    evaluation/training orchestration code (run_experiment.py) can
    treat all three uniformly."""

    def fit(self, texts: list[str], labels: list[int]) -> "ContentBaseline": ...
    def predict(self, texts: list[str]) -> np.ndarray: ...
    def predict_proba(self, texts: list[str]) -> np.ndarray: ...  # P(Fake) per text


@dataclass
class TfidfLogisticRegressionBaseline:
    """TF-IDF + Logistic Regression. Real, executable, tested."""

    max_features: int = 20_000
    ngram_range: tuple[int, int] = (1, 2)
    C: float = 1.0
    random_state: int = 42

    def __post_init__(self) -> None:
        self._vectorizer = TfidfVectorizer(
            max_features=self.max_features, ngram_range=self.ngram_range
        )
        self._model = LogisticRegression(C=self.C, random_state=self.random_state, max_iter=1000)
        self._fitted = False

    def fit(self, texts: list[str], labels: list[int]) -> "TfidfLogisticRegressionBaseline":
        if len(texts) != len(labels):
            raise ValueError(f"texts ({len(texts)}) and labels ({len(labels)}) length mismatch")
        if len(texts) == 0:
            raise ValueError("Cannot fit on empty data")
        X = self._vectorizer.fit_transform(texts)
        self._model.fit(X, labels)
        self._fitted = True
        return self

    def predict(self, texts: list[str]) -> np.ndarray:
        self._check_fitted()
        X = self._vectorizer.transform(texts)
        return self._model.predict(X)

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        self._check_fitted()
        X = self._vectorizer.transform(texts)
        # predict_proba returns [P(class 0), P(class 1)]; class 1 = Fake
        return self._model.predict_proba(X)[:, 1]

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError("Baseline must be fit() before predict()/predict_proba()")


@dataclass
class TfidfRandomForestBaseline:
    """TF-IDF + Random Forest. Real, executable, tested."""

    max_features: int = 20_000
    ngram_range: tuple[int, int] = (1, 2)
    n_estimators: int = 200
    max_depth: int | None = None
    random_state: int = 42

    def __post_init__(self) -> None:
        self._vectorizer = TfidfVectorizer(
            max_features=self.max_features, ngram_range=self.ngram_range
        )
        self._model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_state,
        )
        self._fitted = False

    def fit(self, texts: list[str], labels: list[int]) -> "TfidfRandomForestBaseline":
        if len(texts) != len(labels):
            raise ValueError(f"texts ({len(texts)}) and labels ({len(labels)}) length mismatch")
        if len(texts) == 0:
            raise ValueError("Cannot fit on empty data")
        X = self._vectorizer.fit_transform(texts)
        self._model.fit(X, labels)
        self._fitted = True
        return self

    def predict(self, texts: list[str]) -> np.ndarray:
        self._check_fitted()
        X = self._vectorizer.transform(texts)
        return self._model.predict(X)

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        self._check_fitted()
        X = self._vectorizer.transform(texts)
        return self._model.predict_proba(X)[:, 1]

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError("Baseline must be fit() before predict()/predict_proba()")


class TextEncoderMLPBaseline:
    """Frozen pretrained sentence-transformers encoder + a small MLP
    classification head (Batch J's third baseline). Uses the same
    frozen encoder as encoders/content_encoder.py, per the Phase 3
    plan's consistency requirement between baseline and GNN content
    features.

    STATUS: split into two parts with different verification status.
    The MLP head (_fit_from_embeddings / _predict_from_embeddings) is
    real torch code, genuinely executed and tested on synthetic
    embedding vectors (torch IS installed in this sandbox) -- see
    tests/unit/test_baselines.py's TextEncoderMLPBaseline tests. The
    full fit(texts, labels)/predict(texts) pipeline additionally calls
    ContentEncoder.encode(), which requires downloading model weights
    from huggingface.co -- confirmed unreachable in this sandbox (see
    encoders/content_encoder.py). So: the trainable head is genuinely
    verified; the end-to-end text-in pipeline is not, specifically at
    the network-dependent encoding step, not because of any code
    defect.
    """

    def __init__(
        self,
        encoder_name: str = "all-MiniLM-L6-v2",
        hidden_dim: int = 128,
        random_state: int = 42,
    ):
        self.encoder_name = encoder_name
        self.hidden_dim = hidden_dim
        self.random_state = random_state
        self._encoder = ContentEncoder(model_name=encoder_name)
        self._model = None
        self._embed_dim = None
        self._fitted = False

    def _build_model(self, embed_dim: int):
        import torch
        import torch.nn as nn

        torch.manual_seed(self.random_state)
        return nn.Sequential(
            nn.Linear(embed_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(self.hidden_dim, 1),
        )

    def fit(
        self, texts: list[str], labels: list[int], *, epochs: int = 50, lr: float = 0.01
    ) -> "TextEncoderMLPBaseline":
        embeddings = self._encoder.encode(texts)  # network-dependent; see class docstring
        self._fit_from_embeddings(embeddings, labels, epochs=epochs, lr=lr)
        return self

    def predict(self, texts: list[str]) -> np.ndarray:
        embeddings = self._encoder.encode(texts)
        return self._predict_from_embeddings(embeddings)

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        embeddings = self._encoder.encode(texts)
        return self._predict_proba_from_embeddings(embeddings)

    # --- embedding-input methods: no network dependency, genuinely
    # executed and tested against synthetic embedding vectors ---

    def _fit_from_embeddings(
        self, embeddings: np.ndarray, labels: list[int], epochs: int = 50, lr: float = 0.01
    ) -> None:
        import torch
        import torch.nn as nn

        if len(embeddings) != len(labels):
            raise ValueError(
                f"embeddings ({len(embeddings)}) and labels ({len(labels)}) length mismatch"
            )
        if len(embeddings) == 0:
            raise ValueError("Cannot fit on empty data")

        embed_dim = embeddings.shape[1]
        self._embed_dim = embed_dim
        self._model = self._build_model(embed_dim)

        X = torch.tensor(embeddings, dtype=torch.float32)
        y = torch.tensor(labels, dtype=torch.float32)
        optimizer = torch.optim.Adam(self._model.parameters(), lr=lr)

        self._model.train()
        for _ in range(epochs):
            optimizer.zero_grad()
            logits = self._model(X).squeeze(-1)
            loss = nn.functional.binary_cross_entropy_with_logits(logits, y)
            loss.backward()
            optimizer.step()
        self._fitted = True

    def _predict_proba_from_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        import torch

        self._check_fitted()
        X = torch.tensor(embeddings, dtype=torch.float32)
        self._model.eval()
        with torch.no_grad():
            logits = self._model(X).squeeze(-1)
            probs = torch.sigmoid(logits)
        return probs.numpy()

    def _predict_from_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        probs = self._predict_proba_from_embeddings(embeddings)
        return (probs >= 0.5).astype(int)

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError("Baseline must be fit() before predict()/predict_proba()")
