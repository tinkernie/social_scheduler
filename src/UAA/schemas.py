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



