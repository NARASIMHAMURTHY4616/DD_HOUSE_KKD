from typing import List, Optional
from backend.app.database.repositories.product_repository import ProductRepository, product_repository


class ProductService:
    def __init__(self, repository: Optional[ProductRepository] = None):
        self.repository = repository or product_repository

    def list_products(self, category: Optional[str] = None) -> List[dict]:
        return self.repository.get_all(category=category)

    def get_product(self, product_id: str) -> Optional[dict]:
        return self.repository.get_by_id(product_id)


product_service = ProductService()
