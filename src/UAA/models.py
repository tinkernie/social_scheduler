from sqlmodel import SQLModel, Field
import uuid
from typing import Optional
from datetime import datetime
from pydantic import EmailStr


class User(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True, nullable=False)
    username: str = Field(index=True, nullable=False, unique=True)
    hashed_pasword: str
    email: EmailStr = Field(index=True, nullable=False, unique=True)
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
