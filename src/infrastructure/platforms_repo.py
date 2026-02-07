# src/infrastructure/platforms_repo.py
from typing import Optional, List
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from src.models.connected_platform import ConnectedPlatform
import uuid
from datetime import datetime

class PlatformsRepository:
    """
    Repository for ConnectedPlatform entity.
    All methods are async and expect an AsyncSession to be injected from the outside.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, cp: ConnectedPlatform) -> ConnectedPlatform:
        """
        Persist a new ConnectedPlatform and return refreshed instance.
        """
        self.session.add(cp)
        await self.session.commit()
        await self.session.refresh(cp)
        return cp

    async def get_by_id(self, id: uuid.UUID) -> Optional[ConnectedPlatform]:
        q = select(ConnectedPlatform).where(ConnectedPlatform.id == id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_by_user_and_provider(self, user_id: str, provider: str) -> Optional[ConnectedPlatform]:
        q = select(ConnectedPlatform).where(
            ConnectedPlatform.user_id == user_id,
            ConnectedPlatform.provider == provider
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_by_provider_user_id(self, provider: str, provider_user_id: str) -> Optional[ConnectedPlatform]:
        q = select(ConnectedPlatform).where(
            ConnectedPlatform.provider == provider,
            ConnectedPlatform.provider_user_id == provider_user_id
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> List[ConnectedPlatform]:
        q = select(ConnectedPlatform).where(ConnectedPlatform.user_id == user_id)
        res = await self.session.execute(q)
        return res.scalars().all()

    async def update_tokens(
        self,
        cp: ConnectedPlatform,
        access_token_enc: str,
        refresh_token_enc: Optional[str],
        expires_at: Optional[datetime],
        meta: Optional[dict] = None
    ) -> ConnectedPlatform:
        """
        Update token fields and optionally meta, token_expires_at and updated_at.
        Commits and returns refreshed instance.
        """
        cp.access_token_enc = access_token_enc
        cp.refresh_token_enc = refresh_token_enc
        cp.token_expires_at = expires_at
        if meta is not None:
            # merge meta shallowly (caller can decide full replace or merge)
            cp.meta = meta
        cp.updated_at = datetime.utcnow()
        self.session.add(cp)
        await self.session.commit()
        await self.session.refresh(cp)
        return cp

    async def update_provider_user_id(self, cp: ConnectedPlatform, provider_user_id: str) -> ConnectedPlatform:
        cp.provider_user_id = provider_user_id
        cp.updated_at = datetime.utcnow()
        self.session.add(cp)
        await self.session.commit()
        await self.session.refresh(cp)
        return cp

    async def delete(self, cp: ConnectedPlatform) -> None:
        """
        Delete the provided ConnectedPlatform instance.
        """
        await self.session.delete(cp)
        await self.session.commit()

    async def delete_by_id(self, id: uuid.UUID) -> None:
        cp = await self.get_by_id(id)
        if cp:
            await self.session.delete(cp)
            await self.session.commit()
