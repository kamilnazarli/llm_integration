from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum


class Category(str, Enum):
    billing = "billing"
    bug = "bug"
    feature = "feature"
    other = "other"

class Urgency(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"

class MessageInput(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

class MessageOutput(BaseModel):
    category: Category
    urgency: Urgency
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(max_length=60)