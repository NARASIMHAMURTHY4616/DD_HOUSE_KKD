from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.schemas.product import ProductListResponse, SingleProductResponse, ProductResponse
from backend.app.services.product_service import product_service

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
def get_products(category: Optional[str] = Query(None, description="Filter by category")):
    """Retrieve all verified DD House products, with optional category filter."""
    products = product_service.list_products(category=category)
    return ProductListResponse(
        success=True,
        count=len(products),
        data=[ProductResponse(**p) for p in products]
    )


@router.get("/{product_id}", response_model=SingleProductResponse)
def get_product(product_id: str):
    """Retrieve a single verified product by its unique product_id."""
    product = product_service.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PRODUCT_NOT_FOUND",
                "message": f"Product with ID '{product_id}' was not found."
            }
        )
    return SingleProductResponse(
        success=True,
        data=ProductResponse(**product)
    )
