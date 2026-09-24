import numpy as np
import pytest
from propagate_research.models.baselines import (
    TextEncoderMLPBaseline,
    TfidfLogisticRegressionBaseline,
    TfidfRandomForestBaseline,
)

_BASELINE_CLASSES = [TfidfLogisticRegressionBaseline, TfidfRandomForestBaseline]

_FAKE_TEXTS = [
    "Scientists shocked by this one weird trick doctors hate",
    "You won't believe what happened next, share before deleted",
    "Secret cure big pharma doesn't want you to know",
    "Aliens confirmed living among us says anonymous insider",
]
_REAL_TEXTS = [
    "The central bank raised interest rates by a quarter point today",
    "Researchers published peer-reviewed findings in a scientific journal",
    "The city council approved the annual budget after public comment",
    "Quarterly earnings met analyst expectations according to the report",
]


def _training_set():
    texts = _FAKE_TEXTS + _REAL_TEXTS
    labels = [1] * len(_FAKE_TEXTS) + [0] * len(_REAL_TEXTS)
    return texts, labels


@pytest.mark.parametrize("baseline_cls", _BASELINE_CLASSES)
def test_baseline_fits_and_predicts(baseline_cls):
    texts, labels = _training_set()
    model = baseline_cls()
    model.fit(texts, labels)
    preds = model.predict(texts)
    assert len(preds) == len(texts)
    assert set(np.unique(preds)).issubset({0, 1})


@pytest.mark.parametrize("baseline_cls", _BASELINE_CLASSES)
def test_baseline_predict_proba_in_valid_range(baseline_cls):
    texts, labels = _training_set()
    model = baseline_cls()
    model.fit(texts, labels)
    probs = model.predict_proba(texts)
    assert len(probs) == len(texts)
    assert np.all((probs >= 0) & (probs <= 1))


@pytest.mark.parametrize("baseline_cls", _BASELINE_CLASSES)
def test_baseline_learns_something_better_than_chance(baseline_cls):
    """Not a strict accuracy bar -- this corpus is small and synthetic
    -- just confirms fit/predict aren't wired backwards or inert."""
    texts, labels = _training_set()
    model = baseline_cls(random_state=0)
    model.fit(texts, labels)
    preds = model.predict(texts)
    accuracy = np.mean(np.array(preds) == np.array(labels))
    assert accuracy >= 0.75


@pytest.mark.parametrize("baseline_cls", _BASELINE_CLASSES)
def test_baseline_predict_before_fit_raises(baseline_cls):
    model = baseline_cls()
    with pytest.raises(RuntimeError):
        model.predict(["some text"])


@pytest.mark.parametrize("baseline_cls", _BASELINE_CLASSES)
def test_baseline_fit_rejects_length_mismatch(baseline_cls):
    model = baseline_cls()
    with pytest.raises(ValueError):
        model.fit(["a", "b"], [0])


@pytest.mark.parametrize("baseline_cls", _BASELINE_CLASSES)
def test_baseline_fit_rejects_empty_data(baseline_cls):
    model = baseline_cls()
    with pytest.raises(ValueError):
        model.fit([], [])


@pytest.mark.parametrize("baseline_cls", _BASELINE_CLASSES)
def test_baseline_deterministic_with_fixed_seed(baseline_cls):
    texts, labels = _training_set()
    model_a = baseline_cls(random_state=7)
    model_a.fit(texts, labels)
    model_b = baseline_cls(random_state=7)
    model_b.fit(texts, labels)
    assert list(model_a.predict(texts)) == list(model_b.predict(texts))


# --- honest-stub checks for the network-dependent encoding step ---


def test_text_encoder_mlp_baseline_is_importable_without_torch():
    model = TextEncoderMLPBaseline()
    assert model.encoder_name == "all-MiniLM-L6-v2"


def test_text_encoder_mlp_baseline_fit_fails_at_network_step_not_silently(monkeypatch):
    """fit(texts, labels) reaches the encoder's ContentEncoder.encode()
    call, which is mocked at the actual external seam
    (sentence_transformers.SentenceTransformer) rather than relying on
    this environment's network being unreachable -- deterministic
    either way, and still confirms the failure is real and specific,
    not a generic crash."""
    import sentence_transformers

    def _raise_weights_unreachable(*args, **kwargs):
        raise OSError("simulated: could not reach huggingface.co")

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", _raise_weights_unreachable)

    model = TextEncoderMLPBaseline()
    with pytest.raises(RuntimeError, match="huggingface"):
        model.fit(["some text"], [1])


def test_text_encoder_mlp_baseline_predict_before_fit_raises():
    model = TextEncoderMLPBaseline()
    with pytest.raises(RuntimeError):
        model._predict_from_embeddings(np.random.randn(2, 16))


# --- MLP head, genuinely executed on synthetic embeddings (no
# network dependency -- torch IS installed in this sandbox) ---


def _synthetic_embeddings(n_per_class: int = 20, embed_dim: int = 32, seed: int = 0):
    rng = np.random.default_rng(seed)
    class0 = rng.normal(loc=-1.0, scale=0.5, size=(n_per_class, embed_dim))
    class1 = rng.normal(loc=1.0, scale=0.5, size=(n_per_class, embed_dim))
    embeddings = np.vstack([class0, class1]).astype(np.float32)
    labels = [0] * n_per_class + [1] * n_per_class
    return embeddings, labels


def test_mlp_head_fits_and_predicts_on_synthetic_embeddings():
    embeddings, labels = _synthetic_embeddings()
    model = TextEncoderMLPBaseline(hidden_dim=16, random_state=0)
    model._fit_from_embeddings(embeddings, labels, epochs=100, lr=0.05)

    preds = model._predict_from_embeddings(embeddings)
    accuracy = np.mean(np.array(preds) == np.array(labels))
    assert accuracy >= 0.85  # well-separated synthetic classes; should be easy


def test_mlp_head_predict_proba_in_valid_range():
    embeddings, labels = _synthetic_embeddings()
    model = TextEncoderMLPBaseline(hidden_dim=16, random_state=0)
    model._fit_from_embeddings(embeddings, labels, epochs=50)
    probs = model._predict_proba_from_embeddings(embeddings)
    assert np.all((probs >= 0) & (probs <= 1))


def test_mlp_head_rejects_length_mismatch():
    model = TextEncoderMLPBaseline()
    with pytest.raises(ValueError):
        model._fit_from_embeddings(np.random.randn(3, 8), [0, 1])


def test_mlp_head_rejects_empty_data():
    model = TextEncoderMLPBaseline()
    with pytest.raises(ValueError):
        model._fit_from_embeddings(np.empty((0, 8)), [])


def test_mlp_head_deterministic_with_fixed_seed():
    embeddings, labels = _synthetic_embeddings()
    model_a = TextEncoderMLPBaseline(hidden_dim=16, random_state=7)
    model_a._fit_from_embeddings(embeddings, labels, epochs=20)
    model_b = TextEncoderMLPBaseline(hidden_dim=16, random_state=7)
    model_b._fit_from_embeddings(embeddings, labels, epochs=20)
    preds_a = model_a._predict_from_embeddings(embeddings)
    preds_b = model_b._predict_from_embeddings(embeddings)
    assert list(preds_a) == list(preds_b)
