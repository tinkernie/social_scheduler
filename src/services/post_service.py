# src/services/post_service.py
from sqlmodel.ext.asyncio.session import AsyncSession
from src.models.post import Post, Schedule
from src.models.connected_platform import ConnectedPlatform
from src.infrastructure.telegram_bot_client import TelegramBotClient
from sqlmodel import select

class PostService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.telegram_client = TelegramBotClient()

    async def create_post(self, user_id: str, payload):
        post = Post(user_id=user_id, title=payload.title, content=payload.content, media_path=payload.media_path, draft=False)
        self.session.add(post)

        await self.telegram_client.publish_post(
            title=post.title,
            content=post.content,
            media_path=post.media_path,
        )

        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def schedule_post(self, post_id: str, payload):
        # validate post exists
        q = select(Post).where(Post.id == post_id)
        res = await self.session.execute(q)
        post = res.scalar_one_or_none()
        if not post:
            raise ValueError("post not found")

        # confirm connected platform exists
        q2 = select(ConnectedPlatform).where(ConnectedPlatform.id == payload.connected_platform_id)
        res2 = await self.session.execute(q2)
        cp = res2.scalar_one_or_none()
        if not cp:
            raise ValueError("connected platform not found")

        sched = Schedule(post_id=post.id, connected_platform_id=cp.id, scheduled_time=payload.scheduled_time)
        self.session.add(sched)
        await self.session.commit()
        await self.session.refresh(sched)
        return sched
