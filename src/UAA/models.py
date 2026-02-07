# src/UAA/models.py
from sqlmodel import SQLModel, Field, Column
from typing import Optional
from datetime import datetime
import uuid
from pydantic import EmailStr
from sqlalchemy import String

class User(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default=None, primary_key=True)
    email: EmailStr = Field(sa_column=Column(String, unique=True, index=True), nullable=False)
    username: str = Field(sa_column=Column(String, unique=True, index=True), nullable=False)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    otp_enabled: bool = Field(default=False)
