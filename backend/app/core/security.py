"""
Password hashing and token primitives.

PRD Batch B / Rules.md §6: Argon2id only, never plaintext, never
logged. This module is the ONLY place password hashing happens —
service.py calls into it rather than touching argon2 directly, so
there is exactly one place to audit for Rule #6 (traceable source)
and the "no plaintext in logs" exit-gate condition.
"""
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# argon2-cffi's default profile already selects the Argon2id variant
# with parameters suitable for interactive login (this is the
# library's own recommended default, not a hand-tuned guess — Rules.md
# §3.1 warns against inventing config with no stated need).
_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False
    return True


def generate_opaque_token() -> str:
    """A high-entropy token for session cookies / password-reset
    links. Only the SHA-256 hash of this value is ever stored
    (session_token_hash / token_hash columns) — the raw value exists
    only in the cookie / the emailed link, never in the database."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Deterministic hash for lookup (unlike Argon2id, which is
    intentionally non-deterministic and unsuitable for indexed
    lookup). This is a lookup key, not a secret-at-rest password, so
    SHA-256 is the appropriate primitive here — not Argon2id."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
