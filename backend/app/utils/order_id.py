from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional, Tuple
from pymongo import ReturnDocument
from pymongo.database import Database
from backend.app.database.connection import get_database

IST = timezone(timedelta(hours=5, minutes=30))


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


def generate_queue_token(db: Optional[Database] = None, dt: Optional[datetime] = None) -> Tuple[str, str, int]:
    """
    Generate an atomic, sequential daily queue token in format QXXX (e.g. Q001, Q002).
    Resets daily by business date in Indian Standard Time (IST).
    Returns (token, date_str, seq).
    """
    target_db = db if db is not None else get_database()
    now = dt or datetime.now(IST)
    date_str = now.strftime("%Y-%m-%d")
    counter_id = f"queue_{date_str}"

    counter_doc = target_db.counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    seq = counter_doc.get("seq", 1)
    token = f"Q{seq:03d}"
    return token, date_str, seq
