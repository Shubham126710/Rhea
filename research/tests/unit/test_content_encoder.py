import pytest
from propagate_research.encoders.content_encoder import ContentEncoder


def test_content_encoder_is_importable_and_constructible_without_sentence_transformers():
    encoder = ContentEncoder()
    assert encoder.model_name == "all-MiniLM-L6-v2"


def test_content_encoder_custom_model_name():
    encoder = ContentEncoder(model_name="a-different-model")
    assert encoder.model_name == "a-different-model"


def test_content_encoder_encode_rejects_empty_input():
    encoder = ContentEncoder()
    with pytest.raises(ValueError):
        encoder.encode([])


def test_content_encoder_encode_raises_clear_error_when_model_weights_unreachable(monkeypatch):
    # Mocked at the actual external seam (sentence_transformers.
    # SentenceTransformer) so this is deterministic regardless of
    # whether this environment happens to have the model weights
    # cached -- exercises the same production OSError-to-RuntimeError
    # wrapping in ContentEncoder._ensure_loaded either way.
    import sentence_transformers

    def _raise_weights_unreachable(*args, **kwargs):
        raise OSError("simulated: could not reach huggingface.co")

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", _raise_weights_unreachable)

    encoder = ContentEncoder()
    with pytest.raises(RuntimeError, match="huggingface"):
        encoder.encode(["some article text"])


def test_content_encoder_embedding_dim_raises_clear_error_when_model_weights_unreachable(
    monkeypatch,
):
    import sentence_transformers

    def _raise_weights_unreachable(*args, **kwargs):
        raise OSError("simulated: could not reach huggingface.co")

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", _raise_weights_unreachable)

    encoder = ContentEncoder()
    with pytest.raises(RuntimeError, match="huggingface"):
        _ = encoder.embedding_dim
