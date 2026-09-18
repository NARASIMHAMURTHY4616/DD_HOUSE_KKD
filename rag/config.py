"""Configuration settings for DD House RAG System.
"""
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Base directory for the RAG module
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

# Ensure workspace root is always in Python path regardless of execution directory
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load .env from workspace root, backend dir, or rag dir
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env")
load_dotenv(BASE_DIR / ".env")

class RAGConfig:
    # Paths
    BASE_DIR: Path = BASE_DIR
    ROOT_DIR: Path = ROOT_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    DOCUMENTS_DIR: Path = BASE_DIR / "documents"
    VECTOR_DB_PATH: Path = BASE_DIR / "vector_store_db"
    
    # Business Contacts
    STORE_PHONE: str = "7013522727"
    STORE_WHATSAPP: str = "7013522727"
    STORE_NAME: str = "DD House"
    
    # LLM Settings (OpenAI-compatible / xAI Grok API)
    LLM_KEY_COOLDOWN_SECONDS: int = int(os.getenv("LLM_KEY_COOLDOWN_SECONDS", "60"))
    
    _raw_key: str = (
        os.getenv("API_KEY") or
        os.getenv("LLM_API_KEY_1") or
        os.getenv("LLM_API_KEY") or
        os.getenv("XAI_API_KEY") or
        os.getenv("GROK_API_KEY") or
        os.getenv("OPENAI_API_KEY") or
        ""
    ).strip().strip("\"'").strip()

    LLM_API_KEY: str = _raw_key
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "grok")

    # Smart Base URL resolution: honors explicit LLM_BASE_URL, otherwise auto-resolves endpoint by key format
    _env_base_url = os.getenv("LLM_BASE_URL")
    if _env_base_url:
        LLM_BASE_URL: str = _env_base_url
    elif _raw_key.startswith("gsk_"):
        LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    else:
        LLM_BASE_URL: str = "https://api.x.ai/v1"

    # Model resolution: honors explicit GROK_MODEL or LLM_MODEL, otherwise defaults
    _env_model = os.getenv("GROK_MODEL") or os.getenv("LLM_MODEL")
    if _env_model:
        LLM_MODEL: str = _env_model
    elif "groq.com" in LLM_BASE_URL or _raw_key.startswith("gsk_"):
        LLM_MODEL: str = "openai/gpt-oss-120b"
    else:
        LLM_MODEL: str = "grok-4.6"

    GROK_MODEL: str = LLM_MODEL
    LLM_TEMPERATURE: float = 0.0
    
    # Embedding Settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    # Retrieval Confidence Threshold (Layer 1 Protection)
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))
    TOP_K: int = int(os.getenv("TOP_K", "4"))
    VECTOR_CANDIDATE_K: int = int(os.getenv("VECTOR_CANDIDATE_K", "8"))
    
    # Hallucination Controlled Fallback
    UNKNOWN_RESPONSE: str = (
        "I don't have verified information about that in the DD House knowledge base. "
        "Please contact DD House at 7013522727."
    )
    TBD_RESPONSE: str = (
        "I don't have verified information about that yet. "
        "Please contact DD House at 7013522727 for confirmation."
    )
    ALLERGEN_TBD_RESPONSE: str = (
        "I don't have verified ingredient/allergen information for that product yet."
    )

settings = RAGConfig()
