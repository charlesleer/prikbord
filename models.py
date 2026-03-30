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
    owner: str
    group_tag: str
    wake_date: date
    urgency: Urgency = Urgency.low
    tags: List[str] = Field(default_factory=list)


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=300)
    owner: Optional[str] = None
    group_tag: Optional[str] = None
    wake_date: Optional[date] = None
    urgency: Optional[Urgency] = None
    resolved: Optional[bool] = None
    tags: Optional[List[str]] = None


class NoteOut(NoteBase):
    id: str
    created_at: datetime
    updated_at: datetime
    resolved: bool

    class Config:
        from_attributes = True
