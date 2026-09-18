from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class CustomizationInput(BaseModel):
    flavor: Optional[str] = None
    filling: Optional[str] = None
    toppings: Optional[List[str]] = Field(default_factory=list)
    sauce: Optional[str] = None
    message: Optional[str] = Field(None, description="Message written on the box")


class CustomizationOutput(BaseModel):
    flavor: Optional[str] = None
    filling: Optional[str] = None
    toppings: List[str] = Field(default_factory=list)
    sauce: Optional[str] = None
    message: Optional[str] = None
    note: Optional[str] = "Message is written on the BOX, not on the cake."


class OrderItemInput(BaseModel):
    model_config = {"extra": "ignore"}
    product_id: str
    quantity: int = Field(..., ge=1, description="Quantity must be at least 1")
    customization: Optional[CustomizationInput] = None


class OrderItemOutput(BaseModel):
    product_id: str
    name: str
    quantity: int
    unit_price: float
    subtotal: float
    customization: Optional[CustomizationOutput] = None


class CustomerInput(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., description="10-digit mobile number")


class CustomerOutput(BaseModel):
    name: str
    phone: str


class PaymentInput(BaseModel):
    model_config = {"extra": "ignore"}
    method: str = Field(default="UPI", description="UPI or CASH")


class PaymentOutput(BaseModel):
    method: str
    status: str


class CancellationOutput(BaseModel):
    cancelled: bool
    cancelled_at: Optional[str] = None
    refund_status: Optional[str] = None
    refund_amount: Optional[float] = None


class CreateOrderRequest(BaseModel):
    customer: CustomerInput
    items: List[OrderItemInput] = Field(..., min_length=1, description="At least one item required")
    pickup_time: str = Field(..., min_length=1, description="Requested pickup time or pre-booking slot")
    payment: Optional[PaymentInput] = Field(default_factory=PaymentInput)


class PickupVerificationRequest(BaseModel):
    pickup_pin: str = Field(..., min_length=4, max_length=4, description="4-digit pickup PIN")


# Responses
class OrderCreatedData(BaseModel):
    order_id: str
    pickup_pin: str  # Given once upon creation to the customer
    customer: CustomerOutput
    items: List[OrderItemOutput]
    total_amount: float
    pickup_time: str
    payment: PaymentOutput
    status: str
    cancellation: CancellationOutput
    created_at: str
    updated_at: str


class OrderPublicData(BaseModel):
    order_id: str
    customer: CustomerOutput
    items: List[OrderItemOutput]
    total_amount: float
    pickup_time: str
    payment: PaymentOutput
    status: str
    cancellation: CancellationOutput
    created_at: str
    updated_at: str
    # Notice pickup_pin is excluded from public lookup


class OrderStatusData(BaseModel):
    order_id: str
    status: str
    pickup_time: str
    payment: PaymentOutput
    cancellation: CancellationOutput


class OrderResponse(BaseModel):
    success: bool = True
    data: Any
