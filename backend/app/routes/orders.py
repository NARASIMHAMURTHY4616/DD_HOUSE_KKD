from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, Header, HTTPException, Query, status
from pydantic import BaseModel

from backend.app.config.settings import settings
from backend.app.schemas.order import (
    CreateOrderRequest,
    PickupVerificationRequest,
    OrderResponse,
)
from backend.app.services.order_service import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


class StatusUpdateRequest(BaseModel):
    status: str


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrderResponse)
def create_order(request: CreateOrderRequest):
    """
    Create a new customer order.
    Server calculates total strictly from MongoDB verified prices.
    Generates unique Order ID and 4-digit Pickup PIN.
    """
    order = order_service.create_order(request)
    return OrderResponse(
        success=True,
        data=order
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    """
    Retrieve order details.
    For security, the pickup PIN is excluded and customer phone is masked for public lookup.
    """
    order = order_service.get_order(order_id, include_pin=False)
    return OrderResponse(
        success=True,
        data=order
    )


@router.get("/{order_id}/status", response_model=OrderResponse)
def get_order_status(order_id: str):
    """
    Get order tracking status, pickup time, and cancellation status.
    """
    order_status = order_service.get_order_status(order_id)
    return OrderResponse(
        success=True,
        data=order_status
    )


@router.get("/{order_id}/queue", response_model=OrderResponse)
def get_order_queue(order_id: str):
    """
    Get customer queue status: token, active position, and estimated ready time.
    Excludes pickup PIN and full customer phone.
    """
    queue_data = order_service.get_order_queue(order_id)
    return OrderResponse(
        success=True,
        data=queue_data
    )


@router.post("/{order_id}/pickup", response_model=OrderResponse)
def verify_pickup(order_id: str, request: PickupVerificationRequest):
    """
    Verify customer pickup using 4-digit pickup PIN.
    Order must be strictly in 'READY_FOR_PICKUP' state.
    """
    result = order_service.verify_pickup(order_id, request)
    return OrderResponse(
        success=True,
        data=result
    )


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: str):
    """
    Cancel an order:
    - Within 5 minutes: full refund (FULL_REFUND)
    - After 5 minutes: MANUAL_REVIEW_REQUIRED (no fabricated deductions)
    """
    result = order_service.cancel_order(order_id)
    return OrderResponse(
        success=True,
        data=result
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: str,
    request: StatusUpdateRequest,
    x_store_token: Optional[str] = Header(None, alias="X-Store-Token", description="Internal Store Authorization Token")
):
    """
    Internal/Store management endpoint to update order status
    (e.g., PENDING_PAYMENT -> CONFIRMED -> PREPARING -> READY_FOR_PICKUP).
    Protected by X-Store-Token header.
    Never exposes pickup_pin.
    """
    if not x_store_token or x_store_token != settings.STORE_INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED_STORE_ACCESS",
                "message": "Store authorization required to update order status."
            }
        )

    updated = order_service.update_order_status(order_id, request.status)
    return OrderResponse(
        success=True,
        data=updated
    )
