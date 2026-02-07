# src/models/post.py
from sqlmodel import SQLModel, Field, Column
from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import String, JSON

class Post(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    title: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    media_path: Optional[str] = Field(default=None)  # object storage path
    draft: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Schedule(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default=None, primary_key=True)
    post_id: uuid.UUID = Field(foreign_key="post.id", index=True)
    connected_platform_id: uuid.UUID = Field(foreign_key="connectedplatform.id", index=True)
    scheduled_time: datetime
    status: str = Field(default="pending")  # pending, running, published, failed
    last_error: Optional[str] = Field(default=None)
    external_post_id: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    meta: Optional[dict] = Field(sa_column=Column(JSON), default={})
    created_at: datetime = Field(default_factory=datetime.utcnow)
