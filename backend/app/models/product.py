from typing import Optional
from pydantic import BaseModel, Field


class ProductModel(BaseModel):
    product_id: str = Field(..., description="Unique product ID, e.g. CB001")
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Category: Cake Bowl, Brownie, or Cake Lollipop")
    price: float = Field(..., ge=0, description="Base price in INR")
    available: bool = Field(default=True, description="Availability status")
    customizable: bool = Field(default=False, description="Whether product can be customized")

    class Config:
        from_attributes = True
