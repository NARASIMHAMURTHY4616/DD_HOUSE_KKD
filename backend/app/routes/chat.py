from fastapi import APIRouter
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Chat / RAG"])


@router.post("", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """
    Forward customer question to the grounded DD House RAG knowledge pipeline.
    If RAG service is unavailable, returns a clean RAG_SERVICE_UNAVAILABLE error.
    """
    response_data = await chat_service.forward_to_rag(request)
    return ChatResponse(
        success=True,
        data=response_data
    )
