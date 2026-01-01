import os
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import uuid


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(entered_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(entered_password, hashed_password)


def create_access_token(subject: any, expires_delta: timedelta or None = None) -> dict:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    payload = {"sub": str(subject), "exp": int(expire), "jti": jti}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token, "exp": int(expire.timestamp()), "jti": jti}


def create_refresh_token(subject: any, expires_delta: timedelta or None = None) -> dict:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {"sub": str(subject), "exp": int(expire), "jti": jti}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token, "exp": int(expire.timestamp()), "jti": jti}


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
