from typing import List, Optional
from pydantic import BaseModel, Field


class ProductResponse(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    available: bool
    customizable: bool


class ProductListResponse(BaseModel):
    success: bool = True
    count: int
    data: List[ProductResponse]


class SingleProductResponse(BaseModel):
    success: bool = True
    data: ProductResponse
