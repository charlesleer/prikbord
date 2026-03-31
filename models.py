from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class NoteBase(BaseModel):
    title: str = Field(..., max_length=80)
    description: Optional[str] = Field(None, max_length=300)
    owner: str = Field(..., max_length=100)
    group_tag: str = Field(..., max_length=100)
    wake_date: Optional[date] = None
    urgency: Urgency = Urgency.low
    tags: List[str] = Field(default_factory=list)


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=300)
    owner: Optional[str] = Field(None, max_length=100)
    group_tag: Optional[str] = Field(None, max_length=100)
    wake_date: Optional[date] = None
    urgency: Optional[Urgency] = None
    resolved: Optional[bool] = None
    tags: Optional[List[str]] = None


class NoteOut(NoteBase):
    id: str
    board_id: str
    note_order: int
    created_at: datetime
    updated_at: datetime
    resolved: bool

    class Config:
        from_attributes = True


class ImportNoteItem(BaseModel):
    title: str = Field(..., max_length=80)
    description: Optional[str] = Field(None, max_length=300)
    owner: str = Field(..., max_length=100)
    group_tag: str = Field(..., max_length=100)
    wake_date: str
    urgency: Urgency = Urgency.low
    tags: List[str] = Field(default_factory=list)
    resolved: bool = False


class ImportPayload(BaseModel):
    notes: List[ImportNoteItem]


class BoardCreate(BaseModel):
    name: str = Field(..., max_length=80)


class BoardOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
