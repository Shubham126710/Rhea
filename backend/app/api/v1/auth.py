"""
/api/v1/auth/* — Phase 1 (Phases.md).
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.dependencies import get_current_user
from app.auth.exceptions import AccountThrottled, InvalidCredentials, InvalidOrExpiredToken
from app.auth.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequestRequest,
    SignupRequest,
    UserPublic,
)
from app.core.config import Settings, get_settings
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# PRD Batch B: HttpOnly + Secure + SameSite. SameSite=lax is the
# judgment call here (not pinned by PRD) — balances CSRF protection
# with normal top-level-navigation login flows; flagged in the
# implementation report rather than silently chosen without mention.
_COOKIE_SAMESITE: Literal["lax"] = "lax"


def _set_session_cookie(response: Response, settings: Settings, raw_token: str, expires_at) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        expires=expires_at,
        httponly=True,
        # ROOT-CAUSE FIX: this was hardcoded True. A browser silently
        # refuses to store a Secure-flagged cookie on a response that
        # didn't arrive over HTTPS (RFC 6265bis §4.1.2.5) -- and local
        # dev serves the backend over plain http://localhost:8000 /
        # http://127.0.0.1:8000 throughout this project. Login would
        # return 200 with a valid body (so the frontend's own state
        # looked authenticated), but the cookie itself never actually
        # persisted in the browser, so the very next real request had
        # no session to present and the backend correctly (not
        # falsely) 401'd it -- the exact "Initialize Processing ->
        # Not authenticated" symptom. Fixed by tying Secure to the
        # actual environment, the standard pattern for this flag:
        # secure=False only for the literal "development" environment
        # string, so any other/unexpected value fails safe (stays
        # Secure) rather than silently weakening it in production.
        secure=settings.ENVIRONMENT != "development",
        samesite=_COOKIE_SAMESITE,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")


@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    service.signup(
        db, email=payload.email, display_name=payload.display_name, password=payload.password
    )
    # Enumeration-safe: identical response whether or not the email
    # was already registered (Master Build Batch P).
    return MessageResponse(
        message="If this email is available, an account has been created. You can now log in."
    )


@router.post("/login", response_model=UserPublic)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserPublic:
    try:
        user, raw_token, expires_at = service.login(
            db,
            settings,
            email=payload.email,
            password=payload.password,
            remember_device=payload.remember_device,
        )
    except AccountThrottled as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except InvalidCredentials as exc:
        # Same message for "no such user" and "wrong password" —
        # enumeration-safe.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        ) from exc

    _set_session_cookie(response, settings, raw_token, expires_at)
    return UserPublic.model_validate(user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(get_current_user),
) -> MessageResponse:
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if raw_token:
        service.logout(db, raw_token)
    _clear_session_cookie(response, settings)
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(user)


@router.post("/password-reset/request", response_model=MessageResponse)
def password_reset_request(
    payload: PasswordResetRequestRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    reset_base_url = f"{settings.FRONTEND_BASE_URL}/reset-password"
    service.request_password_reset(
        db, settings, email=payload.email, reset_link_base_url=reset_base_url
    )
    return MessageResponse(
        message="If this email is registered, a password reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        service.confirm_password_reset(
            db, raw_token=payload.token, new_password=payload.new_password
        )
    except InvalidOrExpiredToken as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        ) from exc
    return MessageResponse(message="Password has been reset. You can now log in.")


@router.delete("/me", response_model=MessageResponse)
def delete_account(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    service.delete_account(db, user)
    _clear_session_cookie(response, settings)
    return MessageResponse(message="Account deleted.")
