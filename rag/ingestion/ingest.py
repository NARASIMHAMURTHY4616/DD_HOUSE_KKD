"""Ingestion pipeline script: loads, validates, generates docs, chunks, and indexes knowledge.
"""
from typing import Dict, Any
from rag.ingestion.loader import DataLoader
from rag.ingestion.validator import DataValidator
from rag.ingestion.document_builder import DocumentBuilder
from rag.ingestion.chunker import SemanticChunker
from rag.retrieval.vector_store import VectorStore

def run_ingestion() -> Dict[str, Any]:
    print("=== Starting DD House RAG Ingestion Pipeline ===")
    
    # 1. Load data
    loader = DataLoader()
    records = loader.load_all_json_records()
    conflicts_data = loader.load_external_conflicts()
    conflicts = conflicts_data.get("conflicts", [])
    print(f"[1/4] Loaded {len(records)} structured records and {len(conflicts)} conflict mappings.")

    # 2. Validate data authority and conflict consistency
    val_summary = DataValidator.validate_dataset(records, conflicts)
    if not val_summary["valid"]:
        print(f"[VALIDATION FAILED]: {val_summary['record_errors']}")
        raise ValueError(f"Dataset validation failed: {val_summary['record_errors']}")
    print(f"[2/4] Validation passed successfully: {val_summary['type_counts']}")

    # 3. Build markdown documentation
    builder = DocumentBuilder(loader)
    builder.build_all()
    print("[3/4] Markdown documentation built/synchronized.")

    # 4. Chunk records
    chunker = SemanticChunker()
    chunks = chunker.chunk_records(records)
    print(f"[4/4] Created {len(chunks)} semantic chunks with full metadata.")

    # 5. Populate Vector Store
    vector_store = VectorStore()
    vector_store.clear()
    vector_store.add_chunks(chunks)
    print(f"=== Ingestion complete: {len(chunks)} chunks indexed into Vector Store ===")

    return {
        "status": "success",
        "total_records": len(records),
        "total_chunks": len(chunks),
        "total_conflicts": len(conflicts),
        "validation": val_summary
    }

if __name__ == "__main__":
    run_ingestion()
