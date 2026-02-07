# src/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional
import structlog
import os

from ..dependencies.db import get_session_dep
from ..UAA.repository import UserRepository
from ..UAA.services import UserService, AuthenticationError
from ..UAA.schemas import UserCreate, Token
from ..UAA import utils


from ..infrastructure.email import send_email
from datetime import datetime

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# cookie config (in prod set secure=True)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, session: AsyncSession = Depends(get_session_dep)):
    repo = UserRepository(session)
    svc = UserService(repo, session)
    try:
        created = await svc.register_user(user_in)
        return {"id": str(created.id), "email": created.email, "username": created.username}
    except ValueError as e:
        logger.info("register_validation_failed", error=str(e), email=user_in.email)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(form_data: UserCreate, response: Response, session: AsyncSession = Depends(get_session_dep)):
    """
    Expects JSON: {"email": "...", "username": "...", "password": "..."}
    We use email+password for auth; username included for compatibility.
    Returns access token in body and sets refresh token as HttpOnly cookie.
    """
    repo = UserRepository(session)
    svc = UserService(repo, session)
    try:
        user = await svc.authenticate_user(form_data.email, form_data.password)
    except AuthenticationError as e:
        # Do not reveal whether email exists
        logger.warning("login_failed", reason=str(e), email=form_data.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # issue tokens
    tokens = await svc.issue_tokens(user)
    access = tokens["access"]
    refresh = tokens["refresh"]

    # set refresh token cookie (HttpOnly). secure flag should be enabled in production.
    cookie_max_age = max(0, refresh["exp"] - int(datetime.utcnow().timestamp()))
    response.set_cookie(
        key="refresh_token",
        value=refresh["token"],
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=cookie_max_age,
    )
    return {"access_token": access["token"], "token_type": "bearer", "expires_in": access["exp"]}

@router.post("/refresh", response_model=Token)
async def refresh(response: Response, refresh_token: Optional[str] = Cookie(None)):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    repo = None  # not needed here
    svc = None
    try:
        # rotation performed in service
        from ..UAA.services import UserService  # dynamic import if needed
        new = await UserService(repo=None, session=None).refresh_tokens(refresh_token)
        # set new refresh cookie
        cookie_max_age = max(0, new["refresh"]["exp"] - int(datetime.utcnow().timestamp()))
        response.set_cookie(
            key="refresh_token",
            value=new["refresh"]["token"],
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=cookie_max_age,
        )
        return {"access_token": new["access"]["token"], "token_type": "bearer", "expires_in": new["access"]["exp"]}
    except AuthenticationError as e:
        logger.warning("refresh_failed", reason=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except Exception as e:
        logger.exception("refresh_unexpected_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.post("/logout")
async def logout(response: Response, access_token: Optional[str] = None, refresh_token: Optional[str] = Cookie(None), revoke_all: bool = False):
    """
    Logout endpoint. Frontend should:
      - send Authorization: Bearer <access_token> header OR pass access_token in body
      - refresh token cookie will be read automatically (if present)
    revoke_all: if True, revoke all refresh tokens for this user (logout everywhere)
    """
    # resolve tokens from cookie/header/body as appropriate; here we accept optional access token param for flexibility
    try:
        svc = UserService(repo=None, session=None)  # Note: methods used don't need DB session for revocation
        await svc.logout(access_token=access_token, refresh_token=refresh_token, revoke_all=revoke_all)
        # remove cookie client-side by setting empty cookie
        response.delete_cookie("refresh_token")
        return {"ok": True}
    except Exception as e:
        logger.exception("logout_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed")

# ---------- OTP endpoints ----------
@router.post("/otp/request")
async def otp_request(user_id: str, action: str = "login", session: AsyncSession = Depends(get_session_dep)):
    """
    Request an OTP for a given (user_id, action).
    - تولید OTP و ذخیره در Redis (utils.request_otp)
    - ارسال OTP به ایمیل کاربر (send_email)
    - در حالت production، OTP در response برگردانده نمی‌شود؛ فقط HTTP 202 یا پیام مناسب برمی‌گردد.
      در حالت development، برای تست OTP مقدار آن نیز بازگردانده می‌شود.
    """
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    try:
        otp = await utils.request_otp(user_id, action)
    except RuntimeError as e:
        # rate-limited
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.exception("otp_generation_failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="OTP generation failed")

    # ارسال ایمیل — قالب ساده
    subject = "Your verification code"
    plain = f"Your verification code is: {otp}\nThis code is valid for a short time."
    html = f"<p>Your verification code is: <strong>{otp}</strong></p><p>This code is valid for a short time.</p>"

    try:
        # ارسال ایمیل به آدرس ثبت‌شده کاربر
        await send_email(to_email=user.email, subject=subject, plain_text=plain, html=html)
    except Exception as e:
        # اگر ارسال ایمیل با خطا مواجه شد، OTP را حذف کن تا بازیابی و ارسال بعدی تمیز باشد
        await utils.redis_client.delete(f"otp:{action}:{user_id}")
        logger.exception("otp_email_send_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    # پاسخ: در محیط production عدد otp را برنگردانیم (security)
    if os.getenv("ENVIRONMENT", "development").lower() == "development":
        # توسعه: بازگرداندن OTP برای تست
        return {"status": "sent", "method": "email", "otp": otp}
    else:
        # production: فقط acknowledge
        return {"status": "sent", "method": "email"}

@router.post("/otp/verify")
async def otp_verify(user_id: str, action: str, otp: str):
    try:
        ok = await utils.verify_otp(user_id, action, otp)
        if not ok:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        return {"verified": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("otp_verify_failed", error=str(e))
        raise HTTPException(status_code=500, detail="OTP verification failed")
