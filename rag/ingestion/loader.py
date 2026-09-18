"""Loader for DD House structured business data and documents.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from rag.config import settings

class DataLoader:
    def __init__(self, data_dir: Path = None, documents_dir: Path = None):
        self.data_dir = data_dir or settings.DATA_DIR
        self.documents_dir = documents_dir or settings.DOCUMENTS_DIR

    def load_all_json_records(self) -> List[Dict[str, Any]]:
        """Load all structured JSON records across data files."""
        all_records: List[Dict[str, Any]] = []
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        all_records.extend(content)
                    elif isinstance(content, dict):
                        # If file contains raw_external_records or conflicts
                        if "raw_external_records" in content:
                            all_records.extend(content["raw_external_records"])
                        else:
                            all_records.append(content)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        return all_records

    def load_external_conflicts(self) -> Dict[str, Any]:
        """Load external reference data and conflict mappings."""
        conflict_file = self.data_dir / "external_references.json"
        if conflict_file.exists():
            with open(conflict_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"external_source": {}, "raw_external_records": [], "conflicts": []}

    def load_markdown_documents(self) -> Dict[str, str]:
        """Load markdown files from the documents directory."""
        docs: Dict[str, str] = {}
        for file_path in self.documents_dir.glob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    docs[file_path.stem] = f.read()
            except Exception as e:
                print(f"Error loading document {file_path}: {e}")
        return docs
