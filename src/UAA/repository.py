from sqlalchemy.ext.asyncio import AsyncSession
from .models import User
from sqlmodel import select
from datetime import datetime
import uuid
from typing import Optional



class UserRepository:
    def __init__(self, db_session:AsyncSession):
        self.db_session = db_session


    async def create_user(self , user: User) -> User:
        self.db_session.add(user)
        await self.db_session.commit()
        await self.db_session.refresh(user)
        return user
    

    async def update_last_login(self , user: User)-> User:
        user.last_login = datetime.utcnow()
        self.db_session.add(user)
        await self.db_session.commit()
        self.db_session.refresh(user)
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        query = select(User).where(User.id == user_id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str)-> Optional[User]:
        query = select(User).where(User.email == email)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    
