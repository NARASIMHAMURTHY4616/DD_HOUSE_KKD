from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CustomizationModel(BaseModel):
    flavor: Optional[str] = None
    filling: Optional[str] = None
    toppings: List[str] = Field(default_factory=list)
    sauce: Optional[str] = None
    message: Optional[str] = None
    note: Optional[str] = "Message is written on the BOX, not on the cake."


class OrderItemModel(BaseModel):
    product_id: str
    name: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)
    subtotal: float = Field(..., ge=0)
    customization: Optional[CustomizationModel] = None


class CustomerModel(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=10, max_length=10)


class PaymentModel(BaseModel):
    method: str = Field(..., description="UPI or CASH")
    status: str = Field(..., description="PENDING, PAID, FAILED, REFUNDED, PARTIALLY_REFUNDED")


class CancellationModel(BaseModel):
    cancelled: bool = False
    cancelled_at: Optional[datetime] = None
    refund_status: Optional[str] = None
    refund_amount: Optional[float] = None


class QueueModel(BaseModel):
    token: str
    position: Optional[int] = None
    queue_date: str
    seq: int
    estimated_ready_at: Optional[str] = None


class OrderModel(BaseModel):
    order_id: str
    pickup_pin: str
    customer: CustomerModel
    items: List[OrderItemModel]
    total_amount: float = Field(..., ge=0)
    pickup_time: str
    payment: PaymentModel
    status: str = Field(default="PENDING_PAYMENT")
    cancellation: CancellationModel = Field(default_factory=CancellationModel)
    queue: Optional[QueueModel] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
