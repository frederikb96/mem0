from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator, validator


class MemoryBase(BaseModel):
    content: str
    metadata_: Optional[dict] = Field(default_factory=dict)

class MemoryCreate(MemoryBase):
    user_id: UUID
    app_id: UUID


class Category(BaseModel):
    name: str


class App(BaseModel):
    id: UUID
    name: str


class Memory(MemoryBase):
    id: UUID
    user_id: UUID
    app_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    state: str
    categories: Optional[List[Category]] = None
    app: App

    model_config = ConfigDict(from_attributes=True)

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    metadata_: Optional[dict] = None
    state: Optional[str] = None


class MemoryResponse(BaseModel):
    id: UUID
    content: str
    created_at: int
    state: str
    app_id: UUID
    app_name: str
    categories: List[str]
    metadata_: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def extract_from_orm(cls, data: Any) -> dict:
        # If it's already a dict, return as-is
        if isinstance(data, dict):
            return data

        # Handle ORM object
        result = {
            'id': data.id,
            'content': data.content,
            'created_at': data.created_at,
            'state': data.state.value if hasattr(data.state, 'value') else str(data.state),
            'app_id': data.app_id,
            'app_name': data.app.name if hasattr(data, 'app') and data.app else 'Unknown',
            'categories': [cat.name for cat in data.categories] if hasattr(data, 'categories') and data.categories else [],
            'metadata_': data.metadata_ if hasattr(data, 'metadata_') else None,
        }
        return result

    @validator('created_at', pre=True)
    def convert_to_epoch(cls, v):
        if isinstance(v, datetime):
            return int(v.timestamp())
        return v

class PaginatedMemoryResponse(BaseModel):
    items: List[MemoryResponse]
    total: int
    page: int
    size: int
    pages: int


class AttachmentCreate(BaseModel):
    content: str
    id: Optional[UUID] = None


class AttachmentUpdate(BaseModel):
    content: str


class AttachmentResponse(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
