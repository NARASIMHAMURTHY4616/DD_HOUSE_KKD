from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pymongo import ReturnDocument
from backend.app.database.connection import get_database


class OrderRepository:
    def __init__(self, db=None):
        self._db = db

    @property
    def collection(self):
        db = self._db if self._db is not None else get_database()
        return db.orders

    def create(self, order_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a newly created order document."""
        doc_to_insert = dict(order_doc)
        self.collection.insert_one(doc_to_insert)
        # Remove MongoDB _id from returned dict
        doc_to_insert.pop("_id", None)
        return doc_to_insert

    def get_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve order by unique order_id."""
        return self.collection.find_one({"order_id": order_id}, {"_id": 0})

    def update_order(self, order_id: str, update_fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields in an order document."""
        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        return self.collection.find_one_and_update(
            {"order_id": order_id},
            {"$set": update_fields},
            projection={"_id": 0},
            return_document=ReturnDocument.AFTER
        )

    def mark_picked_up(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Transition order to PICKED_UP status."""
        return self.update_order(order_id, {
            "status": "PICKED_UP"
        })

    def cancel_order(
        self,
        order_id: str,
        refund_status: Optional[str],
        refund_amount: Optional[float],
        cancelled_at: str,
        payment_status: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Cancel order with recorded refund details."""
        updates: Dict[str, Any] = {
            "status": "CANCELLED",
            "cancellation": {
                "cancelled": True,
                "cancelled_at": cancelled_at,
                "refund_status": refund_status,
                "refund_amount": refund_amount
            }
        }
        if payment_status:
            updates["payment.status"] = payment_status

        return self.collection.find_one_and_update(
            {"order_id": order_id},
            {"$set": updates},
            projection={"_id": 0},
            return_document=ReturnDocument.AFTER
        )


order_repository = OrderRepository()
