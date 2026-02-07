# src/UAA/services.py
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
import structlog

from .models import User
from .repository import UserRepository
from .schemas import UserCreate
from . import utils

logger = structlog.get_logger(__name__)

# brute-force constants
LOGIN_ATTEMPT_WINDOW_SECONDS = 300
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300

class AuthenticationError(Exception):
    pass

class UserService:
    def __init__(self, repo: UserRepository, session: AsyncSession):
        self.repo = repo
        self.session = session

    async def register_user(self, user_in: UserCreate) -> User:
        utils.assert_password_policy(user_in.password)
        existing = await self.repo.get_by_email(user_in.email)
        if existing:
            logger.debug("register_email_exists", email=user_in.email)
            raise ValueError("email already registered")

        existing_username = await self.repo.get_by_username(user_in.username)
        if existing_username:
            logger.debug("register_username_exists", username=user_in.username)
            raise ValueError("username already taken")

        hashed = utils.hash_password(user_in.password)
        user = User(email=user_in.email, username=user_in.username, hashed_password=hashed)
        created = await self.repo.create(user)
        logger.info("user_registered", user_id=str(created.id), email=created.email)
        return created

    async def _is_locked(self, user_id: str) -> bool:
        key = f"la:lock:{user_id}"
        return await utils.redis_client.exists(key) == 1

    async def _increment_login_attempts(self, user_id: str) -> int:
        key = f"la:attempts:{user_id}"
        attempts = await utils.redis_client.incr(key)
        if attempts == 1:
            await utils.redis_client.expire(key, LOGIN_ATTEMPT_WINDOW_SECONDS)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            await utils.redis_client.set(f"la:lock:{user_id}", "1", ex=LOCKOUT_SECONDS)
            logger.warning("user_locked_due_to_failed_logins", user_id=user_id)
        return attempts

    async def _reset_login_attempts(self, user_id: str) -> None:
        await utils.redis_client.delete(f"la:attempts:{user_id}")
        await utils.redis_client.delete(f"la:lock:{user_id}")

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.repo.get_by_email(email)
        if not user:
            logger.debug("auth_failed_unknown_email", email=email)
            raise AuthenticationError("invalid credentials")

        if await self._is_locked(str(user.id)):
            logger.warning("auth_attempt_on_locked_user", user_id=str(user.id))
            raise AuthenticationError("account temporarily locked due to failed login attempts")

        if not utils.verify_password(password, user.hashed_password):
            attempts = await self._increment_login_attempts(str(user.id))
            logger.info("auth_failed_wrong_password", user_id=str(user.id), attempts=attempts)
            raise AuthenticationError("invalid credentials")

        await self._reset_login_attempts(str(user.id))
        await self.repo.update_last_login(user)
        logger.info("auth_success", user_id=str(user.id), email=user.email)
        return user

    async def issue_tokens(self, user: User) -> dict:
        subject = str(user.id)
        access = utils.create_access_token(subject)
        refresh = utils.create_refresh_token(subject)
        await utils.store_refresh_jti(refresh["jti"], subject, refresh["exp"])
        logger.info("tokens_issued", user_id=subject, access_jti=access["jti"], refresh_jti=refresh["jti"])
        return {"access": access, "refresh": refresh}

    async def refresh_tokens(self, old_refresh_token: str) -> dict:
        try:
            payload = utils.decode_token(old_refresh_token)
        except Exception as e:
            logger.warning("invalid_refresh_token_decode", error=str(e))
            raise AuthenticationError("invalid refresh token")

        if payload.get("type") != "refresh":
            logger.warning("token_type_not_refresh", payload_type=payload.get("type"))
            raise AuthenticationError("invalid token type")

        old_jti = payload.get("jti")
        user_id = payload.get("sub")
        if not await utils.is_refresh_valid(old_jti):
            logger.warning("refresh_token_not_found_in_redis", jti=old_jti)
            raise AuthenticationError("refresh token revoked or invalid")

        await utils.revoke_refresh_jti(old_jti)
        access = utils.create_access_token(user_id)
        new_refresh = utils.create_refresh_token(user_id)
        await utils.store_refresh_jti(new_refresh["jti"], user_id, new_refresh["exp"])
        logger.info("refresh_rotated", user_id=user_id, old_jti=old_jti, new_jti=new_refresh["jti"])
        return {"access": access, "refresh": new_refresh}

    async def logout(self, access_token: Optional[str] = None, refresh_token: Optional[str] = None, revoke_all: bool = False):
        if refresh_token:
            try:
                payload = utils.decode_token(refresh_token)
            except Exception:
                payload = None
            if payload and payload.get("type") == "refresh":
                jti = payload.get("jti")
                sub = payload.get("sub")
                await utils.revoke_refresh_jti(jti)
                logger.info("refresh_revoked_on_logout", jti=jti, user_id=sub)
                if revoke_all and sub:
                    await utils.revoke_all_refresh_for_user(sub)

        if access_token:
            try:
                payload = utils.decode_token(access_token)
            except Exception:
                payload = None
            if payload and payload.get("type") == "access":
                jti = payload.get("jti")
                exp = payload.get("exp")
                if jti and exp:
                    await utils.blacklist_access_jti(jti, exp)
                    logger.info("access_blacklisted_on_logout", jti=jti)
    async def request_otp(self, user_id: str, action: str = "login", ttl: int = 300) -> str:
        return await utils.request_otp(user_id, action, ttl)

    async def verify_otp(self, user_id: str, action: str, otp: str) -> bool:
        return await utils.verify_otp(user_id, action, otp)
