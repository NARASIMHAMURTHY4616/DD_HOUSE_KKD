"""FastAPI router for DD House RAG customer assistant.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from rag.pipeline.rag_pipeline import RAGPipeline
from rag.ingestion.loader import DataLoader
from rag.ingestion.ingest import run_ingestion

router = APIRouter(prefix="/api/rag", tags=["DD House RAG"])
pipeline = RAGPipeline()

class ChatSource(BaseModel):
    category: str
    name: Optional[str] = None
    source_type: str

class ChatRequest(BaseModel):
    question: str = Field(..., description="Customer question", json_schema_extra={"example": "How much is the Triple Chocolate cake bowl?"})

class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    confidence: float
    sources: List[ChatSource]

@router.post("/chat", response_model=ChatResponse, summary="Chat with DD House Assistant")
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Answers customer inquiries using ONLY verified DD House knowledge."""
    res = pipeline.query(request.question)
    return ChatResponse(
        answer=res["answer"],
        grounded=res["grounded"],
        confidence=res["confidence"],
        sources=[ChatSource(**s) for s in res.get("sources", [])]
    )

@router.get("/health", summary="RAG System Health Check")
def health_check() -> Dict[str, Any]:
    """Check health status and indexed knowledge count."""
    return {
        "status": "healthy",
        "service": "DD House RAG Assistant",
        "indexed_chunks": len(pipeline.retriever.vector_store.chunks),
        "authority_model": "Type 1 Verified > Type 2 External > Type 3 Assumption"
    }

@router.get("/conflicts", summary="Inspect Data Conflicts")
def get_conflicts() -> Dict[str, Any]:
    """View logged conflicts between primary business data and external sources."""
    loader = DataLoader()
    return loader.load_external_conflicts()

@router.post("/ingest", summary="Trigger Knowledge Ingestion")
def ingest_endpoint() -> Dict[str, Any]:
    """Re-runs ingestion pipeline to sync updated data."""
    try:
        summary = run_ingestion()
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )
