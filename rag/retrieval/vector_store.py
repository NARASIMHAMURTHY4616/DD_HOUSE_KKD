"""Vector store implementation with ChromaDB support and high-performance local fallback.
"""
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from rag.config import settings
from rag.ingestion.chunker import DocumentChunk
from rag.ingestion.embedder import EmbedderFactory, BaseEmbedder

class VectorStore:
    def __init__(self, storage_path: Optional[Path] = None, embedder: Optional[BaseEmbedder] = None):
        self.storage_path = storage_path or settings.VECTOR_DB_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or EmbedderFactory.get_embedder()
        self.chunks: List[DocumentChunk] = []
        self.embeddings: np.ndarray = np.empty((0, 0))
        self.index_file = self.storage_path / "index.pkl"
        self._load()

    def clear(self):
        """Clear all indexed data."""
        self.chunks = []
        self.embeddings = np.empty((0, 0))
        if self.index_file.exists():
            self.index_file.unlink()

    def add_chunks(self, chunks: List[DocumentChunk]):
        """Embed and index new chunks."""
        if not chunks:
            return

        texts = [c.text for c in chunks]
        
        # If embedder has fit method (e.g. BuiltinSemanticEmbedder)
        if hasattr(self.embedder, "fit"):
            self.embedder.fit(texts)

        emb_list = self.embedder.embed_documents(texts)
        emb_matrix = np.array(emb_list, dtype=np.float32)

        self.chunks = chunks
        self.embeddings = emb_matrix
        self._save()

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_fn: Optional[Any] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search top_k most similar chunks to query text."""
        if len(self.chunks) == 0:
            self._load()
            if len(self.chunks) == 0:
                return []

        q_vec = np.array(self.embedder.embed_query(query), dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_vec = q_vec / q_norm

        # Compute cosine similarity
        doc_norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        doc_norms[doc_norms == 0] = 1e-10
        norm_embeddings = self.embeddings / doc_norms

        sims = np.dot(norm_embeddings, q_vec)

        results: List[Tuple[DocumentChunk, float]] = []
        # Rank by score descending
        ranked_indices = np.argsort(sims)[::-1]

        for idx in ranked_indices:
            chunk = self.chunks[idx]
            score = float(sims[idx])

            # Apply optional metadata filter
            if filter_fn and not filter_fn(chunk):
                continue

            results.append((chunk, score))
            if len(results) >= top_k:
                break

        return results

    def _save(self):
        """Persist index and chunks to disk."""
        with open(self.index_file, "wb") as f:
            pickle.dump({"chunks": self.chunks, "embeddings": self.embeddings, "embedder": self.embedder}, f)

    def _load(self):
        """Load index from disk if present."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "rb") as f:
                    data = pickle.load(f)
                    self.chunks = data.get("chunks", [])
                    self.embeddings = data.get("embeddings", np.empty((0, 0)))
                    loaded_emb = data.get("embedder")
                    if loaded_emb and hasattr(loaded_emb, "vectorizer") and hasattr(loaded_emb.vectorizer, "transformer_list"):
                        self.embedder = loaded_emb
                    else:
                        # Re-fit fresh hybrid embedder if loaded index had old schema
                        if self.chunks and hasattr(self.embedder, "fit"):
                            texts = [c.text for c in self.chunks]
                            self.embedder.fit(texts)
                            self.embeddings = np.array(self.embedder.embed_documents(texts), dtype=np.float32)
            except Exception as e:
                print(f"Warning loading index: {e}")
