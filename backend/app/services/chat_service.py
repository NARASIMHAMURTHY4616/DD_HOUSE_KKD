import logging
import httpx
from fastapi import HTTPException, status
from backend.app.config.settings import settings
from backend.app.schemas.chat import ChatRequest, ChatResponseData

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, rag_url: str = settings.RAG_SERVICE_URL):
        self.rag_url = rag_url.rstrip("/")

    async def forward_to_rag(self, request: ChatRequest) -> ChatResponseData:
        """
        Forward customer question to the RAG service.
        Strict Privacy: Only message content is forwarded. Zero customer/order data is shared.
        Zero Fabrication: Never returns fabricated answers if RAG service is unreachable.
        """
        target_url = f"{self.rag_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    target_url,
                    json={"message": request.message}
                )
                if response.status_code == 200:
                    data = response.json()
                    # Expecting {"response": "..."} or {"data": {"response": "..."}}
                    answer = data.get("response") or data.get("data", {}).get("response", "")
                    return ChatResponseData(response=answer, source="rag")
                else:
                    logger.error(f"RAG service returned error status {response.status_code}: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail={
                            "code": "RAG_SERVICE_UNAVAILABLE",
                            "message": f"The DD House knowledge assistant is currently unavailable. Please try again later or contact the store at {settings.STORE_PHONE}."
                        }
                    )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(f"Could not connect to RAG service at {target_url}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "RAG_SERVICE_UNAVAILABLE",
                    "message": f"The DD House knowledge assistant is currently unavailable. Please try again later or contact the store at {settings.STORE_PHONE}."
                }
            )


chat_service = ChatService()
