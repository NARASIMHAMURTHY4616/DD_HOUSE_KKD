from datetime import datetime
import re
from typing import List, Optional
from pydantic import BaseModel, Field

# Verified Customization Allowed Options
ALLOWED_FLAVORS = [
    "vanilla", "chocolate", "red velvet", "butterscotch", 
    "oreo", "nutella", "fruit flavours", "other flavours available in the menu"
]

ALLOWED_FILLINGS = [
    "chocolate cream", "nutella", "oreo cream", "caramel", "fruit filling"
]

ALLOWED_TOPPINGS = [
    "chocolate chips", "oreo pieces", "sprinkles", "nuts", "brownie pieces", "cherries"
]

ALLOWED_SAUCES = [
    "chocolate", "white chocolate", "caramel", "nutella"
]


def validate_phone(phone: str) -> str:
    cleaned = re.sub(r"\D", "", phone)
    if len(cleaned) == 12 and cleaned.startswith("91"):
        cleaned = cleaned[2:]
    if len(cleaned) != 10:
        raise ValueError(f"Phone number must be a valid 10-digit number. Got: '{phone}'")
    return cleaned


def mask_phone(phone: str) -> str:
    """Mask phone number preserving only the last 4 digits (e.g. ******3210)."""
    try:
        cleaned = validate_phone(phone)
    except ValueError:
        cleaned = phone
    if len(cleaned) >= 4:
        return f"{'*' * (len(cleaned) - 4)}{cleaned[-4:]}"
    return "*" * len(cleaned)


def validate_pickup_time(pickup_time: str) -> str:
    """
    Validate requested pickup time:
    - Must be a valid 24-hour time ('HH:MM') or ISO format string.
    - Must fall within store operating hours: 16:00 to 23:00 IST.
    """
    if not pickup_time or not isinstance(pickup_time, str):
        raise ValueError("Pickup time is required.")

    pickup_time = pickup_time.strip()

    # Attempt to match 24-hour HH:MM format
    hh_mm_match = re.match(r"^(\d{1,2}):(\d{2})$", pickup_time)
    if hh_mm_match:
        hour = int(hh_mm_match.group(1))
        minute = int(hh_mm_match.group(2))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Invalid pickup time format '{pickup_time}'. Hour must be 00-23 and minute 00-59.")
    else:
        # Attempt to match ISO format
        try:
            dt = datetime.fromisoformat(pickup_time)
            hour = dt.hour
            minute = dt.minute
        except Exception:
            raise ValueError(f"Invalid pickup time format '{pickup_time}'. Expected 'HH:MM' or ISO format.")

    # Check store operating hours: 16:00 to 23:00 IST
    pickup_minutes = hour * 60 + minute
    store_open_minutes = 16 * 60   # 16:00 (4 PM)
    store_close_minutes = 23 * 60  # 23:00 (11 PM)

    if pickup_minutes < store_open_minutes or pickup_minutes > store_close_minutes:
        raise ValueError(f"Store is closed. Pickup time '{pickup_time}' is outside operating hours (16:00 to 23:00 IST).")

    return pickup_time


def validate_customization(category: str, customization: Optional[dict]) -> Optional[dict]:
    """
    Validates customization against product category rules:
    - Cake bowls can be customized.
    - Brownies CANNOT be customized.
    - Cake Lollipops CANNOT be customized.
    """
    if not customization:
        return None

    # Check if category supports customization
    if category != "Cake Bowl":
        raise ValueError(f"Customization is not available for '{category}'. Only 'Cake Bowl' products can be customized.")

    # Validate flavor if provided
    flavor = customization.get("flavor")
    if flavor and flavor.strip().lower() not in ALLOWED_FLAVORS:
        raise ValueError(f"Flavour '{flavor}' is not in the list of verified available flavours.")

    # Validate filling if provided
    filling = customization.get("filling")
    if filling and filling.strip().lower() not in ALLOWED_FILLINGS:
        raise ValueError(f"Filling '{filling}' is not in the list of verified available fillings.")

    # Validate toppings if provided
    toppings = customization.get("toppings", [])
    if toppings:
        for t in toppings:
            if t.strip().lower() not in ALLOWED_TOPPINGS:
                raise ValueError(f"Topping '{t}' is not in the list of verified available toppings.")

    # Validate sauce/drizzle if provided
    sauce = customization.get("sauce")
    if sauce and sauce.strip().lower() not in ALLOWED_SAUCES:
        raise ValueError(f"Sauce/drizzle '{sauce}' is not in the list of verified available sauces.")

    # Message on box
    message = customization.get("message")
    if message:
        message = message.strip()

    return {
        "flavor": flavor,
        "filling": filling,
        "toppings": toppings,
        "sauce": sauce,
        "message": message,
        "note": "Message is written on the BOX, not on the cake."
    }
