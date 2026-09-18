from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.config.settings import settings
from backend.app.database.repositories.order_repository import OrderRepository, order_repository
from backend.app.database.repositories.product_repository import ProductRepository, product_repository
from backend.app.schemas.order import CreateOrderRequest, PickupVerificationRequest
from backend.app.utils.order_id import IST, generate_order_id, generate_pickup_pin, generate_queue_token
from backend.app.utils.validators import mask_phone, validate_customization, validate_phone, validate_pickup_time


class OrderService:
    def __init__(
        self,
        order_repo: Optional[OrderRepository] = None,
        product_repo: Optional[ProductRepository] = None
    ):
        self.order_repo = order_repo or order_repository
        self.product_repo = product_repo or product_repository

    def create_order(self, request: CreateOrderRequest) -> Dict[str, Any]:
        """
        Validate order request, enforce server-side prices, validate customizations,
        generate Order ID and PIN, and insert into MongoDB.
        """
        # Validate Customer Phone
        try:
            valid_phone = validate_phone(request.customer.phone)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_PHONE", "message": str(e)}
            )

        customer_name = request.customer.name.strip()
        if not customer_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_CUSTOMER_NAME", "message": "Customer name cannot be empty."}
            )

        # Validate Pickup Time
        try:
            valid_pickup_time = validate_pickup_time(request.pickup_time)
        except ValueError as e:
            err_msg = str(e)
            err_code = "STORE_CLOSED" if "closed" in err_msg.lower() else "INVALID_PICKUP_TIME"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": err_code, "message": err_msg}
            )

        if not request.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "EMPTY_ORDER", "message": "Order must contain at least one item."}
            )

        # Server-side pricing & customization verification
        verified_items: List[Dict[str, Any]] = []
        total_amount: float = 0.0

        for item in request.items:
            if item.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_QUANTITY",
                        "message": f"Quantity for product '{item.product_id}' must be greater than 0."
                    }
                )

            # Query product from MongoDB
            product = self.product_repo.get_by_id(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "PRODUCT_NOT_FOUND",
                        "message": f"Product with ID '{item.product_id}' was not found in catalog."
                    }
                )

            if not product.get("available", True):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "PRODUCT_UNAVAILABLE",
                        "message": f"Product '{product['name']}' is currently not available."
                    }
                )

            # Validate customization rules
            customization_data = item.customization.model_dump() if item.customization else None
            # Filter out empty dicts or all-None customization
            has_customization = customization_data and any(v for v in customization_data.values() if v)

            if has_customization:
                try:
                    verified_customization = validate_customization(product["category"], customization_data)
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"code": "INVALID_CUSTOMIZATION", "message": str(e)}
                    )
            else:
                verified_customization = None

            # Strictly use database verified unit price
            verified_unit_price = float(product["price"])
            item_subtotal = round(verified_unit_price * item.quantity, 2)
            total_amount += item_subtotal

            verified_items.append({
                "product_id": product["product_id"],
                "name": product["name"],
                "quantity": item.quantity,
                "unit_price": verified_unit_price,
                "subtotal": item_subtotal,
                "customization": verified_customization
            })

        total_amount = round(total_amount, 2)

        # Payment details - server strictly controls payment status
        pay_method = (request.payment.method if request.payment and request.payment.method else "UPI").upper()
        if pay_method not in ["UPI", "CASH"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_PAYMENT_METHOD", "message": "Payment method must be 'UPI' or 'CASH'."}
            )

        # Server-controlled initial status
        if pay_method == "CASH":
            pay_status = settings.CASH_PAYMENT_DEFAULT_STATUS
            order_status = settings.CASH_ORDER_DEFAULT_STATUS
        else:
            # For UPI, advance payment is required; without payment confirmation starts PENDING
            pay_status = "PENDING"
            order_status = "PENDING_PAYMENT"

        now_iso = datetime.now(timezone.utc).isoformat()
        order_id = generate_order_id()
        pickup_pin = generate_pickup_pin()

        # Atomic Queue Token generation (daily sequential, reset in IST)
        token, queue_date, seq = generate_queue_token()

        # Calculate current active orders ahead in queue
        active_ahead = self.order_repo.collection.count_documents({
            "queue.queue_date": queue_date,
            "status": {"$in": ["PENDING_PAYMENT", "CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]}
        })
        initial_position = active_ahead + 1

        # Calculate estimated ready time (Normal ~15 mins, Rush up to ~20 mins in IST)
        now_ist = datetime.now(IST)
        prep_minutes = 15 if active_ahead <= 2 else min(15 + (active_ahead - 2) * 2, 20)
        estimated_ready_at = (now_ist + timedelta(minutes=prep_minutes)).isoformat()

        queue_data = {
            "token": token,
            "position": initial_position,
            "queue_date": queue_date,
            "seq": seq,
            "estimated_ready_at": estimated_ready_at
        }

        order_doc: Dict[str, Any] = {
            "order_id": order_id,
            "pickup_pin": pickup_pin,
            "customer": {
                "name": customer_name,
                "phone": valid_phone
            },
            "items": verified_items,
            "total_amount": total_amount,
            "pickup_time": valid_pickup_time,
            "payment": {
                "method": pay_method,
                "status": pay_status
            },
            "status": order_status,
            "cancellation": {
                "cancelled": False,
                "cancelled_at": None,
                "refund_status": None,
                "refund_amount": None
            },
            "queue": queue_data,
            "created_at": now_iso,
            "updated_at": now_iso
        }

        created_order = self.order_repo.create(order_doc)
        return created_order

    def calculate_queue_position(self, order_doc: Dict[str, Any]) -> Optional[int]:
        """
        Dynamically calculate active queue position for an order.
        Orders in terminal states (PICKED_UP, CANCELLED) are inactive (position = 0).
        For active orders, count active orders on the same business date with seq <= order's seq.
        """
        current_status = order_doc.get("status")
        if current_status not in ["PENDING_PAYMENT", "CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]:
            return 0

        queue_info = order_doc.get("queue")
        if not queue_info or not isinstance(queue_info, dict):
            return None

        queue_date = queue_info.get("queue_date")
        seq = queue_info.get("seq")
        if not queue_date or seq is None:
            return None

        active_count = self.order_repo.collection.count_documents({
            "queue.queue_date": queue_date,
            "status": {"$in": ["PENDING_PAYMENT", "CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]},
            "queue.seq": {"$lte": seq}
        })
        return max(1, active_count)

    def get_order(self, order_id: str, include_pin: bool = False) -> Dict[str, Any]:
        """Retrieve order by order_id, masking pickup_pin and phone for public lookups."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ORDER_NOT_FOUND", "message": f"Order with ID '{order_id}' was not found."}
            )
        order_copy = dict(order)
        if not include_pin:
            order_copy.pop("pickup_pin", None)
        if "customer" in order_copy and "phone" in order_copy["customer"]:
            order_copy["customer"] = dict(order_copy["customer"])
            order_copy["customer"]["phone"] = mask_phone(order_copy["customer"]["phone"])
        if "queue" in order_copy and order_copy["queue"]:
            order_copy["queue"] = dict(order_copy["queue"])
            order_copy["queue"]["position"] = self.calculate_queue_position(order)
        return order_copy

    def update_order_status(self, order_id: str, new_status: str) -> Dict[str, Any]:
        """
        Internal store-management status update adhering to strict order state machine:
        PENDING_PAYMENT -> CONFIRMED -> PREPARING -> READY_FOR_PICKUP
        Terminal states (PICKED_UP, CANCELLED) cannot be changed.
        PICKED_UP can only be reached through pickup PIN verification.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ORDER_NOT_FOUND", "message": f"Order with ID '{order_id}' was not found."}
            )

        current_status = order.get("status")

        # Terminal state check
        if current_status in ["PICKED_UP", "CANCELLED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_STATUS_TRANSITION",
                    "message": f"Order is in terminal state '{current_status}' and cannot be modified."
                }
            )

        # Direct transition to PICKED_UP through PATCH is forbidden
        if new_status == "PICKED_UP":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_STATUS_TRANSITION",
                    "message": "Orders can only be marked as PICKED_UP through the pickup verification endpoint with a valid pickup PIN."
                }
            )

        # Allowed transitions mapping
        allowed_next = {
            "PENDING_PAYMENT": ["CONFIRMED"],
            "CONFIRMED": ["PREPARING"],
            "PREPARING": ["READY_FOR_PICKUP"],
        }

        valid_next_statuses = allowed_next.get(current_status, [])
        if new_status not in valid_next_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_STATUS_TRANSITION",
                    "message": f"Invalid status transition from '{current_status}' to '{new_status}'."
                }
            )

        updates: Dict[str, Any] = {"status": new_status}
        # If moving from PENDING_PAYMENT to CONFIRMED, payment is confirmed as PAID
        if current_status == "PENDING_PAYMENT" and new_status == "CONFIRMED":
            updates["payment.status"] = "PAID"

        updated_order = self.order_repo.update_order(order_id, updates)
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ORDER_NOT_FOUND", "message": f"Order with ID '{order_id}' was not found."}
            )

        # Sanitize response: NEVER expose pickup_pin in status update response
        sanitized = dict(updated_order)
        sanitized.pop("pickup_pin", None)
        if "customer" in sanitized and "phone" in sanitized["customer"]:
            sanitized["customer"] = dict(sanitized["customer"])
            sanitized["customer"]["phone"] = mask_phone(sanitized["customer"]["phone"])
        if "queue" in sanitized and sanitized["queue"]:
            sanitized["queue"] = dict(sanitized["queue"])
            sanitized["queue"]["position"] = self.calculate_queue_position(updated_order)
        return sanitized

    def confirm_payment(self, order_id: str, payment_reference: Optional[str] = None) -> Dict[str, Any]:
        """
        Service extension point for future payment gateway/webhook integration.
        Transitions order from PENDING_PAYMENT to CONFIRMED and payment to PAID.
        """
        return self.update_order_status(order_id, "CONFIRMED")

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Fast status retrieval for customer tracking, including dynamic queue position."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ORDER_NOT_FOUND", "message": f"Order with ID '{order_id}' was not found."}
            )
        queue_info = dict(order.get("queue")) if order.get("queue") else None
        if queue_info:
            queue_info["position"] = self.calculate_queue_position(order)

        return {
            "order_id": order["order_id"],
            "status": order["status"],
            "pickup_time": order["pickup_time"],
            "payment": order["payment"],
            "cancellation": order["cancellation"],
            "queue": queue_info
        }

    def get_order_queue(self, order_id: str) -> Dict[str, Any]:
        """
        Get customer queue information: token, active position, and estimated ready time.
        Excludes pickup PIN and full phone number.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ORDER_NOT_FOUND", "message": f"Order with ID '{order_id}' was not found."}
            )
        queue_info = order.get("queue")
        if not queue_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "QUEUE_NOT_FOUND", "message": f"Queue information for order '{order_id}' was not found."}
            )
        queue_copy = dict(queue_info)
        queue_copy["position"] = self.calculate_queue_position(order)
        return {
            "order_id": order["order_id"],
            "queue": queue_copy,
            "status": order["status"]
        }

    def verify_pickup(self, order_id: str, pin_request: PickupVerificationRequest) -> Dict[str, Any]:
        """
        Verify pickup PIN and transition order to PICKED_UP.
        Strictly requires order to be in 'READY_FOR_PICKUP' status.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ORDER_NOT_FOUND", "message": f"Order with ID '{order_id}' was not found."}
            )

        # Strict state check: must be READY_FOR_PICKUP
        if order.get("status") != "READY_FOR_PICKUP":
            current_status = order.get("status")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_ORDER_STATE",
                    "message": f"Order cannot be picked up. Current status is '{current_status}'. Status must be 'READY_FOR_PICKUP'."
                }
            )

        # PIN verification
        if str(order.get("pickup_pin")) != str(pin_request.pickup_pin).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_PICKUP_PIN", "message": "Incorrect pickup PIN provided."}
            )

        updated_order = self.order_repo.mark_picked_up(order_id)
        return {
            "order_id": order_id,
            "status": "PICKED_UP",
            "message": "Order successfully verified and marked as PICKED_UP."
        }

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel order applying verified 5-minute rule:
        - Within 5 minutes: FULL_REFUND
        - After 5 minutes: MANUAL_REVIEW_REQUIRED (no fabricated refund fee or percentage)
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ORDER_NOT_FOUND", "message": f"Order with ID '{order_id}' was not found."}
            )

        if order.get("status") == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ORDER_ALREADY_CANCELLED", "message": "This order has already been cancelled."}
            )

        if order.get("status") == "PICKED_UP":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ORDER_ALREADY_PICKED_UP", "message": "Order has already been picked up and cannot be cancelled."}
            )

        # Calculate elapsed time from creation
        created_at_str = order.get("created_at")
        try:
            created_at_dt = datetime.fromisoformat(created_at_str)
        except Exception:
            created_at_dt = datetime.now(timezone.utc)

        now = datetime.now(timezone.utc)
        elapsed_seconds = (now - created_at_dt).total_seconds()
        now_iso = now.isoformat()

        if elapsed_seconds <= 300:
            # Within 5 minutes: Full refund
            refund_status = "FULL_REFUND"
            refund_amount = order.get("total_amount", 0.0)
            payment_status = "REFUNDED"
            msg = "Order cancelled within 5-minute window. Eligible for full refund."
        else:
            # After 5 minutes: Depends on time and prep status; no fabricated fixed percentage
            refund_status = "MANUAL_REVIEW_REQUIRED"
            refund_amount = None
            payment_status = None
            msg = "Order cancelled after 5 minutes. Refund requires manual review based on preparation status."

        updated_order = self.order_repo.cancel_order(
            order_id=order_id,
            refund_status=refund_status,
            refund_amount=refund_amount,
            cancelled_at=now_iso,
            payment_status=payment_status
        )

        return {
            "order_id": order_id,
            "status": "CANCELLED",
            "message": msg,
            "cancellation": updated_order.get("cancellation", {})
        }


order_service = OrderService()
