"""End-to-end RAG pipeline for DD House assistant.
"""
from typing import Dict, Any, Optional
from rag.retrieval.retriever import Retriever
from rag.generation.generator import AnswerGenerator
from rag.config import settings

GREETING_WORDS = {
    "hi", "hello", "hii", "hey", "good morning", "good afternoon",
    "good evening", "greetings", "hey there", "hi there", "namaste"
}

class RAGPipeline:
    def __init__(self, retriever: Optional[Retriever] = None, generator: Optional[AnswerGenerator] = None):
        self.retriever = retriever or Retriever()
        self.generator = generator or AnswerGenerator()
        self.last_query_debug: Optional[Dict[str, Any]] = None

    def query(self, question: str) -> Dict[str, Any]:
        """Process question through retrieval, confidence check, and grounded generation."""
        if not question or not question.strip():
            empty_res = {
                "answer": "Please ask a valid question regarding DD House menu, ordering, or store information.",
                "grounded": False,
                "confidence": 0.0,
                "sources": []
            }
            self.last_query_debug = {
                "query": question or "",
                "retrieved_count": 0,
                "results": [],
                "grounded": False,
                "confidence": 0.0,
                "sources": [],
                "answer": empty_res["answer"]
            }
            return empty_res

        q_clean = question.strip()
        q_lower = q_clean.lower().strip("?!., ")

        # Conversational Greeting Handler
        if q_lower in GREETING_WORDS:
            greeting_res = {
                "answer": "Hi! I'm the DD House assistant. I can help with products, prices, customization, ordering, pickup and payment.",
                "grounded": True,
                "confidence": 1.0,
                "sources": []
            }
            self.last_query_debug = {
                "query": q_clean,
                "retrieved_count": 0,
                "results": [],
                "grounded": True,
                "confidence": 1.0,
                "sources": [],
                "answer": greeting_res["answer"],
                "llm_provider": "greeting_handler",
                "llm_model": "none",
                "llm_status": "GREETING",
                "prompt": None
            }
            return greeting_res

        # 1. Two-stage semantic retrieval with diagnostics
        diag = self.retriever.retrieve_with_diagnostics(question.strip(), top_k=settings.TOP_K)
        verified_chunks_tuples = diag["verified_sent"]
        clean_q = diag["clean_query"]

        if not verified_chunks_tuples:
            unknown_res = {
                "answer": settings.UNKNOWN_RESPONSE,
                "grounded": False,
                "confidence": 0.0,
                "sources": []
            }
            self.last_query_debug = {
                "original_query": question.strip(),
                "normalized_query": clean_q,
                "detected_intent": diag.get("detected_intent", "GENERAL"),
                "candidates": diag["candidates"],
                "accepted": diag["accepted"],
                "rejected": diag["rejected"],
                "verified_sent": [],
                "grounded": False,
                "confidence": 0.0,
                "sources": [],
                "answer": unknown_res["answer"],
                "llm_provider": settings.LLM_PROVIDER,
                "llm_model": settings.LLM_MODEL,
                "llm_status": "INSUFFICIENT_CONTEXT",
                "prompt": None
            }
            return unknown_res

        top_confidence = verified_chunks_tuples[0][1]
        retrieved_chunks = [chunk for chunk, _ in verified_chunks_tuples]

        # 2. Generate grounded answer via Grok LLM
        response = self.generator.generate(
            question=question.strip(),
            retrieved_chunks=retrieved_chunks,
            confidence=top_confidence
        )

        self.last_query_debug = {
            "original_query": question.strip(),
            "normalized_query": clean_q,
            "detected_intent": diag.get("detected_intent", "GENERAL"),
            "candidates": diag["candidates"],
            "accepted": diag["accepted"],
            "rejected": diag["rejected"],
            "verified_sent": diag["verified_sent"],
            "grounded": response.get("grounded", False),
            "confidence": response.get("confidence", top_confidence),
            "sources": response.get("sources", []),
            "answer": response.get("answer", ""),
            "llm_provider": response.get("llm_provider", settings.LLM_PROVIDER),
            "llm_model": response.get("llm_model", settings.LLM_MODEL),
            "llm_status": response.get("llm_status", "SUCCESS"),
            "prompt": response.get("prompt")
        }

        return response
