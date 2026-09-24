from app.core.security import (
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_hash_password_is_not_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2id$")


def test_verify_password_correct_and_incorrect():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong password", hashed) is False


def test_generate_opaque_token_is_unique_and_high_entropy():
    tokens = {generate_opaque_token() for _ in range(100)}
    assert len(tokens) == 100
    assert all(len(t) >= 32 for t in tokens)


def test_hash_token_is_deterministic():
    token = generate_opaque_token()
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token
