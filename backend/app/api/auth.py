from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import COOKIE_NAME, get_current_user
from app.core.email import send_password_reset_email
from app.core.rate_limit import check_rate_limit, record_attempt
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    UserRead,
)
from app.services.password_reset import consume_reset_token, create_reset_token

router = APIRouter()
settings = get_settings()


def _cookie_kwargs() -> dict[str, Any]:
    return {
        "httponly": True,
        "secure": not settings.is_dev,
        "samesite": "none" if not settings.is_dev else "lax",
        "path": "/",
        "max_age": settings.access_token_expire_minutes * 60,
    }


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> User:
    client_key = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_key):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts, try again later"
        )

    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        record_attempt(client_key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(user.id)
    response.set_cookie(COOKIE_NAME, token, **_cookie_kwargs())
    return user


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is not None:
        raw_token = create_reset_token(db, user)
        reset_link = f"{settings.frontend_origin}/reset-password?token={raw_token}"
        send_password_reset_email(user.email, reset_link)
    # Always 200 regardless of whether the email matched, so this endpoint
    # can't be used to probe for which email address is registered.
    return {"status": "ok"}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    new_hash = hash_password(payload.new_password)
    if not consume_reset_token(db, payload.token, new_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")
    return {"status": "ok"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "ok"}
