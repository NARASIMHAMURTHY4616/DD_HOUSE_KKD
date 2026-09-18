from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Customer question or inquiry")


class ChatResponseData(BaseModel):
    response: str
    source: Optional[str] = "rag"


class ChatResponse(BaseModel):
    success: bool = True
    data: ChatResponseData
