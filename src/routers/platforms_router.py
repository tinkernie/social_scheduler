# src/routers/platforms_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from src.dependencies.db import get_session_dep
from sqlmodel.ext.asyncio.session import AsyncSession
from src.UAA.utils import create_oauth_state, pop_oauth_state, encrypt_token
from src.infrastructure.platforms_repo import PlatformsRepository
from src.UAA.repository import UserRepository
from src.models.connected_platform import ConnectedPlatform
import os
import httpx
from datetime import datetime, timedelta

router = APIRouter(prefix="/platforms", tags=["platforms"])

INSTAGRAM_CLIENT_ID = os.getenv("INSTAGRAM_CLIENT_ID")
INSTAGRAM_CLIENT_SECRET = os.getenv("INSTAGRAM_CLIENT_SECRET")
INSTAGRAM_REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI")
INSTAGRAM_AUTH_URL = os.getenv("INSTAGRAM_AUTH_URL")
INSTAGRAM_TOKEN_URL = os.getenv("INSTAGRAM_TOKEN_URL")
INSTAGRAM_USERINFO_URL = os.getenv("INSTAGRAM_USERINFO_URL")
INSTAGRAM_SCOPES = os.getenv("INSTAGRAM_SCOPES", "pages_show_list,instagram_basic,pages_read_engagement,pages_manage_posts")

@router.get("/instagram/connect/start")
async def instagram_connect_start(user_id: str, session: AsyncSession = Depends(get_session_dep)):
    if not all([INSTAGRAM_CLIENT_ID, INSTAGRAM_REDIRECT_URI, INSTAGRAM_AUTH_URL]):
        raise HTTPException(status_code=500, detail="Instagram OAuth not configured")

    state = await create_oauth_state(user_id, "instagram")
    params = {
        "client_id": INSTAGRAM_CLIENT_ID,
        "redirect_uri": INSTAGRAM_REDIRECT_URI,
        "state": state,
        "scope": INSTAGRAM_SCOPES,
        "response_type": "code"
    }
    url = httpx.URL(INSTAGRAM_AUTH_URL).include_query_params(**params)
    return {"auth_url": str(url)}

@router.get("/instagram/callback")
async def instagram_callback(code: str | None = None, state: str | None = None, session: AsyncSession = Depends(get_session_dep)):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    payload = await pop_oauth_state(state)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    expected_provider = payload.get("provider")
    user_id = payload.get("user_id")
    if expected_provider != "instagram":
        raise HTTPException(status_code=400, detail="State provider mismatch")

    params = {
        "client_id": INSTAGRAM_CLIENT_ID,
        "redirect_uri": INSTAGRAM_REDIRECT_URI,
        "client_secret": INSTAGRAM_CLIENT_SECRET,
        "code": code,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(INSTAGRAM_TOKEN_URL, params=params)
            resp.raise_for_status()
            token_data = resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Token exchange failed: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail="Token exchange error")

    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        raise HTTPException(status_code=502, detail="No access token returned from provider")

    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

    user_info = None
    if INSTAGRAM_USERINFO_URL:
        try:
            ui_resp = await client.get(INSTAGRAM_USERINFO_URL, params={"access_token": access_token})
            ui_resp.raise_for_status()
            user_info = ui_resp.json()
        except Exception:
            user_info = None

    provider_user_id = None
    if user_info and "id" in user_info:
        provider_user_id = str(user_info["id"])

    access_enc = encrypt_token(access_token)
    refresh_enc = encrypt_token(refresh_token) if refresh_token else None

    repo = PlatformsRepository(session)
    existing = await repo.get_by_user_and_provider(user_id, "instagram")
    if existing:
        await repo.update_tokens(existing, access_enc, refresh_enc, token_expires_at)
        cp = existing
    else:
        cp = ConnectedPlatform(
            user_id=user_id,
            provider="instagram",
            provider_user_id=provider_user_id,
            access_token_enc=access_enc,
            refresh_token_enc=refresh_enc,
            token_expires_at=token_expires_at,
            meta=user_info or {}
        )
        cp = await repo.create(cp)

    return JSONResponse({"status": "connected", "provider": "instagram", "connected_id": str(cp.id)})
