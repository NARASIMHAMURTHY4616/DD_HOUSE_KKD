"""FastAPI application entry point for DD House RAG Assistant.
"""
import sys
from pathlib import Path

# Ensure root directory is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rag.api.routes import router as rag_router
from rag.ingestion.ingest import run_ingestion

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure vector store is initialized on startup."""
    try:
        from rag.retrieval.vector_store import VectorStore
        vs = VectorStore()
        if len(vs.chunks) == 0:
            print("Vector store is empty, triggering automatic ingestion...")
            run_ingestion()
    except Exception as e:
        print(f"Startup ingestion warning: {e}")
    yield

app = FastAPI(
    title="DD House — AI-Powered Cake Ordering & Customer Assistant RAG API",
    version="1.0.0",
    description=(
        "Production-grade, grounded RAG system for DD House cake store in Kakinada. "
        "Strictly adheres to verified business data and prevents hallucinations."
    ),
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include RAG API router
app.include_router(rag_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to DD House Customer Assistant RAG API",
        "docs": "/docs",
        "health": "/api/rag/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rag.main:app", host="0.0.0.0", port=8000, reload=True)
