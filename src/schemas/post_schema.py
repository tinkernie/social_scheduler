# src/schemas/post_schema.py
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

class PostCreate(BaseModel):
    title: Optional[str]
    content: Optional[str]
    media_path: Optional[str]  # path in object storage

class PostRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[str]
    content: Optional[str]
    media_path: Optional[str]
    draft: bool
    created_at: datetime

class ScheduleCreate(BaseModel):
    connected_platform_id: uuid.UUID
    scheduled_time: datetime
