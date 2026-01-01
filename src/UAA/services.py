from .repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import UserCreateSchema
from .models import User
from .utils import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from fastapi import HTTPException, status


class UserService:
    def __init__(self, repo: UserRepository, db_session: AsyncSession):
        self.repo = repo
        self.db_session = db_session

    async def sign_up_user(self, user_in: UserCreateSchema) -> User:
        existing_user = await self.repo.get_user_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists.",
            )

        new_user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_pasword=hash_password(user_in.password),
            full_name=user_in.full_name,
        )

        created_user = await self.repo.create_user(new_user)
        return created_user

    async def sign_in_user(self, email: str, password: str) -> User or None:
        user = self.repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        await self.repo.update_last_login(user)
        return user

    async def issue_tokens(self, user: User):
        subject = str(user.id)
        access = create_access_token(subject)
        refresh = create_refresh_token(subject)
        return {"access": access, "refresh": refresh}

    async def logout(self, *, access_token: str or None = None):
        if access_token:
            try:
                payload = decode_token(access_token)
                return {"ok": True, "sub": payload.get("sub")}
            except Exception:
                return {"ok": True}
        return {"ok": True}
