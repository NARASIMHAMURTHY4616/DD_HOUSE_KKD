from datetime import datetime, timezone
import secrets
from typing import Optional
from pymongo import ReturnDocument
from pymongo.database import Database
from backend.app.database.connection import get_database


def generate_pickup_pin() -> str:
    """Generate a secure 4-digit pickup PIN (1000 - 9999)."""
    return str(secrets.randbelow(9000) + 1000)


def generate_order_id(db: Optional[Database] = None, dt: Optional[datetime] = None) -> str:
    """
    Generate an atomic, guaranteed-unique Order ID in format DDYYYYMMDDXXXX.
    Example: DD202609180001
    """
    target_db = db if db is not None else get_database()
    now = dt or datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    counter_id = f"orders_{date_str}"

    counter_doc = target_db.counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    seq = counter_doc.get("seq", 1)
    return f"DD{date_str}{seq:04d}"
