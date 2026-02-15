# src/routers/post_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from src.dependencies.db import get_session_dep
from src.dependencies.auth import get_current_user
from src.schemas.post_schema import PostCreate, PostRead, ScheduleCreate
from src.services.post_service import PostService
from src.infrastructure.telegram_bot_client import TelegramBotError

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("/", response_model=PostRead)
async def create_post(payload: PostCreate, session: AsyncSession = Depends(get_session_dep), current_user = Depends(get_current_user)):
    svc = PostService(session)
    try:
        post = await svc.create_post(user_id=str(current_user.id), payload=payload)
        return post
    except TelegramBotError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

@router.post("/{post_id}/schedule", response_model=dict)
async def schedule_post(post_id: str, payload: ScheduleCreate, session: AsyncSession = Depends(get_session_dep), current_user = Depends(get_current_user)):
    svc = PostService(session)
    try:
        sched = await svc.schedule_post(post_id, payload)
        return {"schedule_id": str(sched.id), "status": sched.status}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
