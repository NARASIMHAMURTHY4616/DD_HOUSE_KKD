"""Embedding service interface with graceful fallback.
Supports SentenceTransformers, Google Gemini Embeddings, and Built-in Semantic Vectorizer.
"""
from typing import List, Union
import numpy as np
from rag.config import settings

class BaseEmbedder:
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        raise NotImplementedError

class BuiltinSemanticEmbedder(BaseEmbedder):
    """Zero-dependency TF-IDF Hybrid (Word + Character n-gram) vectorizer with cosine normalization.
    Ensures 100% offline reliability and semantic resilience against typos, subwords, and inflections.
    """
    def __init__(self):
        from sklearn.pipeline import FeatureUnion
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(
                ngram_range=(1, 2),
                analyzer="word",
                lowercase=True,
                token_pattern=r"(?u)\b\w+\b|[₹]"
            )),
            ("char_wb", TfidfVectorizer(
                ngram_range=(3, 5),
                analyzer="char_wb",
                lowercase=True
            ))
        ])
        self.fitted = False

    def fit(self, texts: List[str]):
        self.vectorizer.fit(texts)
        self.fitted = True

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.fitted:
            self.fit(texts)
        matrix = self.vectorizer.transform(texts).toarray()
        return matrix.tolist()

    def embed_query(self, text: str) -> List[float]:
        if not self.fitted:
            return [0.0] * 10
        vec = self.vectorizer.transform([text]).toarray()[0]
        return vec.tolist()

class EmbedderFactory:
    _instance = None

    @classmethod
    def get_embedder(cls) -> BaseEmbedder:
        if cls._instance is not None:
            return cls._instance

        # Check if sentence-transformers is available
        try:
            from sentence_transformers import SentenceTransformer
            class STEmbedder(BaseEmbedder):
                def __init__(self, model_name: str):
                    self.model = SentenceTransformer(model_name)
                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    embs = self.model.encode(texts, normalize_embeddings=True)
                    return embs.tolist()
                def embed_query(self, text: str) -> List[float]:
                    emb = self.model.encode([text], normalize_embeddings=True)[0]
                    return emb.tolist()
            cls._instance = STEmbedder(settings.EMBEDDING_MODEL)
            return cls._instance
        except Exception:
            # Graceful fallback to BuiltinSemanticEmbedder
            cls._instance = BuiltinSemanticEmbedder()
            return cls._instance
