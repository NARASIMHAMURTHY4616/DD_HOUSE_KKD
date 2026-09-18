"""Unit tests for RAG retriever, data validator, and chunk metadata integrity.
"""
import pytest
from rag.ingestion.loader import DataLoader
from rag.ingestion.validator import DataValidator
from rag.ingestion.chunker import SemanticChunker
from rag.retrieval.retriever import Retriever

def test_data_validation():
    loader = DataLoader()
    records = loader.load_all_json_records()
    conflicts_data = loader.load_external_conflicts()
    summary = DataValidator.validate_dataset(records, conflicts_data.get("conflicts", []))
    assert summary["valid"] is True
    assert summary["total_records"] >= 70
    assert summary["type_counts"]["business_provided"] >= 50
    assert summary["type_counts"]["external_reference"] >= 5
    assert summary["total_conflicts"] >= 5

def test_chunk_metadata_retention():
    loader = DataLoader()
    records = loader.load_all_json_records()
    chunker = SemanticChunker()
    chunks = chunker.chunk_records(records)
    for c in chunks:
        assert c.chunk_id != ""
        assert c.text != ""
        assert c.category in {"product", "business", "customization", "ordering", "payment", "cancellation_refund", "pickup", "faq", "allergen", "ingredient", "social"}
        assert c.source_type in {"business_provided", "external_reference", "hackathon_assumption", "unknown"}
        assert isinstance(c.verified, bool)

def test_conflict_resolution_phone():
    loader = DataLoader()
    conflicts_data = loader.load_external_conflicts()
    conflicts = conflicts_data.get("conflicts", [])
    phone_conf = next((c for c in conflicts if c["field"] == "phone"), None)
    assert phone_conf is not None
    assert phone_conf["business_provided"] == "7013522727"
    assert phone_conf["external_reference"] == "9948732532"
    assert phone_conf["customer_answer"] == "7013522727"

def test_retriever_product_ranking():
    retriever = Retriever()
    results = retriever.retrieve("What is the price of Triple Chocolate?", top_k=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "99" in top_chunk.text
    assert top_chunk.product == "Triple Chocolate"
    assert score >= 0.85

def test_retriever_customization_brownie_denial():
    retriever = Retriever()
    results = retriever.retrieve("Can I customize brownies?", top_k=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "cannot be customized" in top_chunk.text.lower() or "not eligible" in top_chunk.text.lower()
