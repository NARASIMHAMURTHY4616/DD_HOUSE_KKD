"""Embedding service adapter for backward compatibility.
"""
from rag.ingestion.embedder import EmbedderFactory, BaseEmbedder

def get_embedding_service() -> BaseEmbedder:
    return EmbedderFactory.get_embedder()
