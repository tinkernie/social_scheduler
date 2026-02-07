# src/UAA/utils.py
import os
import secrets
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import structlog
import redis.asyncio as aioredis
from passlib.context import CryptContext
from jose import jwt, JWTError
from cryptography.fernet import Fernet, InvalidToken

logger = structlog.get_logger(__name__)

# Config (env)
SECRET_KEY = os.getenv("SECRET_KEY", "change_me_now")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OAUTH_TOKEN_KEY = os.getenv("OAUTH_TOKEN_KEY")  # must be a base64 key for Fernet, set in prod

if not OAUTH_TOKEN_KEY:
    # dev fallback (not for production)
    OAUTH_TOKEN_KEY = Fernet.generate_key().decode()

# clients
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
fernet = Fernet(OAUTH_TOKEN_KEY.encode())

# --- Password utilities ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception as e:
        logger.exception("password_verify_failed", exc=e)
        return False

def assert_password_policy(password: str) -> None:
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if not any(c.isdigit() for c in password):
        raise ValueError("password must include a digit")
    if not any(c.islower() for c in password):
        raise ValueError("password must include a lowercase letter")
    if not any(c.isupper() for c in password):
        raise ValueError("password must include an uppercase letter")

# --- JWT helpers ---
def _now_ts() -> int:
    return int(datetime.utcnow().timestamp())

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> Dict[str, Any]:
    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "exp": int(expire.timestamp()), "jti": jti, "type": "access", "iat": _now_ts()}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug("create_access_token", sub=subject, jti=jti, exp=payload["exp"])
    return {"token": token, "jti": jti, "exp": payload["exp"]}

def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> Dict[str, Any]:
    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    payload = {"sub": subject, "exp": int(expire.timestamp()), "jti": jti, "type": "refresh", "iat": _now_ts()}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug("create_refresh_token", sub=subject, jti=jti, exp=payload["exp"])
    return {"token": token, "jti": jti, "exp": payload["exp"]}

def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("token_decode_failed", error=str(e))
        raise

# --- Redis-based blacklists and refresh management ---
async def blacklist_access_jti(jti: str, expires_at_ts: int) -> None:
    ttl = max(0, expires_at_ts - _now_ts())
    if ttl <= 0:
        return
    await redis_client.set(f"bl:{jti}", "1", ex=ttl)
    logger.info("access_jti_blacklisted", jti=jti, ttl=ttl)

async def is_access_jti_blacklisted(jti: str) -> bool:
    return await redis_client.exists(f"bl:{jti}") == 1

async def store_refresh_jti(jti: str, user_id: str, expires_at_ts: int) -> None:
    ttl = max(0, expires_at_ts - _now_ts())
    if ttl <= 0:
        raise ValueError("refresh token already expired")
    await redis_client.set(f"rt:{jti}", user_id, ex=ttl)
    await redis_client.sadd(f"rts:{user_id}", jti)
    await redis_client.expire(f"rts:{user_id}", ttl)
    logger.debug("store_refresh_jti", jti=jti, user_id=user_id, ttl=ttl)

async def revoke_refresh_jti(jti: str) -> None:
    user_id = await redis_client.get(f"rt:{jti}")
    await redis_client.delete(f"rt:{jti}")
    if user_id:
        await redis_client.srem(f"rts:{user_id}", jti)
    logger.info("refresh_jti_revoked", jti=jti, user_id=user_id)

async def is_refresh_valid(jti: str) -> bool:
    return await redis_client.exists(f"rt:{jti}") == 1

async def revoke_all_refresh_for_user(user_id: str) -> None:
    set_key = f"rts:{user_id}"
    jtis = await redis_client.smembers(set_key) or set()
    for j in jtis:
        await redis_client.delete(f"rt:{j}")
    await redis_client.delete(set_key)
    logger.info("revoke_all_refresh_for_user", user_id=user_id, revoked_count=len(jtis))

# --- OTP scaffold ---
OTP_LENGTH = 6
OTP_DEFAULT_TTL = 300
OTP_SEND_RATE_SECONDS = 60
OTP_MAX_FAILED_ATTEMPTS = 5
OTP_FAILED_LOCK_SECONDS = 300

def _generate_numeric_otp(length: int = OTP_LENGTH) -> str:
    range_start = 10 ** (length - 1)
    range_end = (10 ** length) - 1
    return str(secrets.randbelow(range_end - range_start + 1) + range_start)

async def request_otp(user_id: str, action: str = "login", ttl: int = OTP_DEFAULT_TTL) -> str:
    rate_key = f"otp:rate:{action}:{user_id}"
    if await redis_client.exists(rate_key):
        logger.info("otp_request_rate_limited", user_id=user_id, action=action)
        raise RuntimeError("OTP request rate limit exceeded")

    otp_code = _generate_numeric_otp()
    otp_key = f"otp:{action}:{user_id}"
    await redis_client.set(otp_key, otp_code, ex=ttl)
    await redis_client.set(rate_key, "1", ex=OTP_SEND_RATE_SECONDS)
    await redis_client.delete(f"otp:attempts:{action}:{user_id}")
    logger.info("otp_created", user_id=user_id, action=action, ttl=ttl)
    return otp_code

async def verify_otp(user_id: str, action: str, otp: str) -> bool:
    lock_key = f"otp:lock:{action}:{user_id}"
    if await redis_client.exists(lock_key):
        logger.info("otp_locked", user_id=user_id, action=action)
        return False

    otp_key = f"otp:{action}:{user_id}"
    stored = await redis_client.get(otp_key)
    if not stored:
        logger.info("otp_missing", user_id=user_id, action=action)
        return False

    if secrets.compare_digest(stored, otp):
        await redis_client.delete(otp_key)
        await redis_client.delete(f"otp:attempts:{action}:{user_id}")
        logger.info("otp_verified", user_id=user_id, action=action)
        return True

    attempts_key = f"otp:attempts:{action}:{user_id}"
    attempts = await redis_client.incr(attempts_key)
    if attempts == 1:
        await redis_client.expire(attempts_key, OTP_DEFAULT_TTL)
    if attempts >= OTP_MAX_FAILED_ATTEMPTS:
        await redis_client.set(lock_key, "1", ex=OTP_FAILED_LOCK_SECONDS)
        logger.warning("otp_locked_due_to_failed_attempts", user_id=user_id, action=action)
    logger.info("otp_failed_attempt", user_id=user_id, action=action, attempts=attempts)
    return False

# --- OAuth token encryption & state ---
def encrypt_token(plaintext: Optional[str]) -> Optional[str]:
    if plaintext is None:
        return None
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_token(ciphertext: Optional[str]) -> Optional[str]:
    if not ciphertext:
        return None
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None

# OAuth state helpers
OAUTH_STATE_TTL = 300

async def create_oauth_state(user_id: str, provider: str) -> str:
    state = secrets.token_urlsafe(32)
    key = f"oauth_state:{state}"
    payload = {"user_id": str(user_id), "provider": provider}
    await redis_client.set(key, json.dumps(payload), ex=OAUTH_STATE_TTL)
    return state

async def pop_oauth_state(state: str) -> Optional[dict]:
    key = f"oauth_state:{state}"
    raw = await redis_client.get(key)
    if not raw:
        return None
    await redis_client.delete(key)
    try:
        return json.loads(raw)
    except Exception:
        return None
