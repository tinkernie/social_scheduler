# src/UAA/repository.py
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from .models import User
from typing import Optional
import uuid
from datetime import datetime

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        q = select(User).where(User.email == email)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        q = select(User).where(User.username == username)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        q = select(User).where(User.id == user_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_last_login(self, user: User):
        user.last_login = datetime.utcnow()
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
