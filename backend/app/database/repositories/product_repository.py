from typing import List, Optional
from backend.app.database.connection import get_database


class ProductRepository:
    def __init__(self, db=None):
        self._db = db

    @property
    def collection(self):
        db = self._db if self._db is not None else get_database()
        return db.products

    def get_all(self, category: Optional[str] = None, available_only: bool = False) -> List[dict]:
        query = {}
        if category:
            query["category"] = category
        if available_only:
            query["available"] = True
        cursor = self.collection.find(query, {"_id": 0})
        return list(cursor)

    def get_by_id(self, product_id: str) -> Optional[dict]:
        return self.collection.find_one({"product_id": product_id}, {"_id": 0})


product_repository = ProductRepository()
