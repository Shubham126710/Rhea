"""
Auth service layer.

Rules.md §2: only Analysis Orchestration may call other modules
directly — but Auth is the one module that IS reached directly from
the API layer for its own endpoints (Architecture.md §5 registers
/api/v1/auth/* directly). This module never imports from
analysis_orchestration, ml_inference, graph_processor, llm_adapter,
or shared_preprocessing — it has no reason to.

Framework-agnostic on purpose: no FastAPI imports here, so these
functions are unit-testable without spinning up the app (Rules.md
§3.1 SRP).
"""
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.email import ConsoleDevEmailSender, EmailSender
from app.auth.exceptions import (
    AccountThrottled,
    InvalidCredentials,
    InvalidOrExpiredToken,
)
from app.core.config import Settings
from app.core.security import (
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.models.auth_session import AuthSession
from app.db.models.password_reset_token import PasswordResetToken
from app.db.models.rate_limit_event import RateLimitEvent
from app.db.models.user import User

_FAILED_LOGIN_KIND_PREFIX = "failed_login:"

# Timing side-channel fix (found in adversarial review): `verify_password`
# takes ~tens of ms (Argon2id is deliberately slow). The original code
# only called it when a user row existed, via short-circuit `or`
# evaluation — meaning a request for a nonexistent email returned
# measurably faster than one for a real email with a wrong password.
# The response body was already enumeration-safe (identical message),
# but timing alone would still leak which case happened. This dummy
# hash is verified against on every "no real user to check" path so
# every rejection path costs the same Argon2id work, computed once at
# import time (it's a fixed decoy, not a secret — no need to be
# request-specific or random).
_DUMMY_HASH_FOR_TIMING_EQUALIZATION = hash_password(
    "propagate-timing-equalization-decoy-password"
)


def _now() -> datetime:
    return datetime.now(UTC)


def _failed_login_kind(email: str) -> str:
    # Keyed by a hash of the email (not the plaintext user_id FK) so
    # throttling behaves identically whether or not the account
    # exists — an attacker can't use "does throttling ever kick in"
    # as an account-enumeration oracle. See implementation report:
    # flagged as a judgment call, rate_limit_events has no dedicated
    # identifier column, so the existing `kind` text field is reused
    # as a composite key rather than adding a migration for this.
    return _FAILED_LOGIN_KIND_PREFIX + hash_token(email.lower())


# --- Signup -----------------------------------------------------------------


def signup(db: Session, *, email: str, display_name: str, password: str) -> None:
    """Always succeeds from the caller's point of view (enumeration-
    safe, Master Build Batch P — applies to signup as well as reset).
    If the email is already registered, this is a silent no-op: no
    duplicate account, no signal to the caller either way."""
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        return
    user = User(
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        role="user",
    )
    db.add(user)
    db.commit()


# --- Login / sessions ---------------------------------------------------------


def _check_throttle(db: Session, settings: Settings, email: str) -> None:
    window_start_cutoff = _now() - timedelta(minutes=settings.FAILED_LOGIN_WINDOW_MINUTES)
    kind = _failed_login_kind(email)

    # Opportunistic cleanup: delete this key's own expired rows on
    # every check, so a key that's throttled and then abandoned
    # doesn't sit in the table forever. This does NOT bound total
    # table growth across every distinct attempted email — that needs
    # a periodic sweep job, which has no infrastructure yet (no
    # scheduler exists before Phase 5/6's job infra). Flagged as a
    # deferred requirement, not silently solved.
    db.query(RateLimitEvent).filter(
        RateLimitEvent.kind == kind, RateLimitEvent.window_start < window_start_cutoff
    ).delete()

    count = db.execute(
        select(func.count())
        .select_from(RateLimitEvent)
        .where(RateLimitEvent.kind == kind, RateLimitEvent.window_start >= window_start_cutoff)
    ).scalar_one()
    if count >= settings.FAILED_LOGIN_MAX_ATTEMPTS:
        db.commit()  # persist the cleanup delete even if we're about to raise
        retry_after = int(
            (
                window_start_cutoff
                + timedelta(minutes=settings.FAILED_LOGIN_WINDOW_MINUTES)
                - _now()
            ).total_seconds()
        )
        raise AccountThrottled(retry_after_seconds=max(retry_after, 1))
    db.commit()


def _record_failed_login(db: Session, email: str) -> None:
    db.add(RateLimitEvent(kind=_failed_login_kind(email), window_start=_now(), count=1))
    db.commit()


def _clear_failed_logins(db: Session, email: str) -> None:
    kind = _failed_login_kind(email)
    db.query(RateLimitEvent).filter(RateLimitEvent.kind == kind).delete()
    db.commit()


def login(
    db: Session, settings: Settings, *, email: str, password: str, remember_device: bool
) -> tuple[User, str, datetime]:
    """Returns (user, raw_session_token, expires_at). Raises
    AccountThrottled or InvalidCredentials (the same exception for
    'no such user' and 'wrong password' — enumeration-safe)."""
    _check_throttle(db, settings, email)

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    # Always perform exactly one Argon2id verification, regardless of
    # which rejection case applies — see the module-level comment on
    # _DUMMY_HASH_FOR_TIMING_EQUALIZATION. Without this, "no such
    # user" and "wrong password" are distinguishable by response time
    # even though the response body is identical.
    if user is not None:
        password_is_correct = verify_password(password, user.password_hash)
    else:
        verify_password(password, _DUMMY_HASH_FOR_TIMING_EQUALIZATION)
        password_is_correct = False

    if user is None or user.deleted_at is not None or not password_is_correct:
        _record_failed_login(db, email)
        raise InvalidCredentials()

    _clear_failed_logins(db, email)

    ttl = (
        timedelta(days=settings.SESSION_REMEMBER_TTL_DAYS)
        if remember_device
        else timedelta(hours=settings.SESSION_TTL_HOURS)
    )
    expires_at = _now() + ttl
    raw_token = generate_opaque_token()
    db.add(
        AuthSession(
            user_id=user.id,
            session_token_hash=hash_token(raw_token),
            expires_at=expires_at,
            remember_device=remember_device,
        )
    )
    db.commit()
    return user, raw_token, expires_at


def get_user_by_session_token(db: Session, raw_token: str) -> User | None:
    token_hash = hash_token(raw_token)
    session_row = db.execute(
        select(AuthSession).where(
            AuthSession.session_token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > _now(),
        )
    ).scalar_one_or_none()
    if session_row is None:
        return None
    user = db.get(User, session_row.user_id)
    if user is None or user.deleted_at is not None:
        return None
    return user


def logout(db: Session, raw_token: str) -> None:
    token_hash = hash_token(raw_token)
    session_row = db.execute(
        select(AuthSession).where(AuthSession.session_token_hash == token_hash)
    ).scalar_one_or_none()
    if session_row is not None and session_row.revoked_at is None:
        session_row.revoked_at = _now()
        db.commit()


def revoke_all_sessions_for_user(db: Session, user_id: UUID) -> None:
    db.query(AuthSession).filter(
        AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
    ).update({"revoked_at": _now()})
    db.commit()


# --- Password reset -----------------------------------------------------------


def request_password_reset(
    db: Session,
    settings: Settings,
    *,
    email: str,
    reset_link_base_url: str,
    email_sender: EmailSender | None = None,
) -> None:
    """Enumeration-safe: always returns None regardless of whether the
    account exists. Only sends an email / creates a token row when it
    does."""
    email_sender = email_sender or ConsoleDevEmailSender()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or user.deleted_at is not None:
        return

    raw_token = generate_opaque_token()
    expires_at = _now() + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )
    )
    db.commit()

    reset_link = f"{reset_link_base_url}?token={raw_token}"
    email_sender.send_password_reset_email(user.email, reset_link)


def confirm_password_reset(db: Session, *, raw_token: str, new_password: str) -> None:
    token_hash = hash_token(raw_token)
    token_row = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if (
        token_row is None
        or token_row.used_at is not None
        or token_row.expires_at <= _now()
    ):
        raise InvalidOrExpiredToken()

    user = db.get(User, token_row.user_id)
    if user is None or user.deleted_at is not None:
        raise InvalidOrExpiredToken()

    user.password_hash = hash_password(new_password)
    token_row.used_at = _now()
    db.commit()

    # A password reset is a credible signal of compromise/recovery —
    # invalidate existing sessions so a stolen session cookie doesn't
    # survive the reset. Not explicitly stated in PRD, but follows
    # directly from Batch B's "explicit ... session invalidation"
    # principle applied to account deletion; flagged as a reasonable
    # extension rather than silently assumed.
    revoke_all_sessions_for_user(db, user.id)


# --- Account deletion -----------------------------------------------------------


def delete_account(db: Session, user: User) -> None:
    user.deleted_at = _now()
    db.commit()
    revoke_all_sessions_for_user(db, user.id)
    # Architecture.md §6.5 describes sessions and password_reset_tokens
    # as FK-cascade-deleted on account deletion (a hard delete of the
    # user row). Phase 1 uses a soft delete instead (see the docs
    # update accompanying this change, which documents this as the
    # actual Phase 1 design rather than leaving the two silently
    # apart). Sessions are handled above via revocation. Outstanding
    # password_reset_tokens were previously left untouched — harmless
    # in practice because confirm_password_reset already checks
    # deleted_at, but an unused, unexpired token for a deleted account
    # sitting in the table serves no purpose. Deleted explicitly here
    # rather than left to expire.
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
    db.commit()
