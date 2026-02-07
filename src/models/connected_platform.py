# src/models/connected_platform.py
from sqlmodel import SQLModel, Field, Column
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import String, JSON

class ConnectedPlatform(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    provider: str = Field(sa_column=Column(String, index=True))
    provider_user_id: Optional[str] = Field(sa_column=Column(String), default=None)
    access_token_enc: str
    refresh_token_enc: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    meta: Optional[dict] = Field(sa_column=Column(JSON), default={})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
