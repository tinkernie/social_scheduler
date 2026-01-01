from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid


class UserCreateSchema(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class UserRetriveSchema(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
    last_login: Optional[str] = None

class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None



# ina ro chat gpt goft ezafe konam

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenPayload(BaseModel):
    sub: str
    exp: int
    jti: str
