"""Intent detector for query classification, multi-intent detection,
and retrieval prioritization in the DD House RAG Assistant.
"""
import re
from typing import List, Dict, Set

class IntentDetector:
    @staticmethod
    def detect_intents(query: str) -> List[str]:
        """Detect one or more retrieval intents from the query."""
        if not query:
            return ["GENERAL"]

        q = query.lower().strip()
        intents: List[str] = []

        # 1. Foreign / Out-of-scope check (Japan, PM of India, joke, stock market, etc.)
        if any(w in q for w in ["japan", "tokyo", "prime minister", "president", "joke", "stock market", "weather", "delhi", "mumbai", "hyderabad", "bangalore", "vijayawada"]):
            return ["UNKNOWN"]

        # 2. Social Media & Online Links
        if any(w in q for w in ["social", "social-media", "instagram", "online", "links", "handle", "page"]):
            intents.append("SOCIAL")

        # 3. Business Hours & Timings
        if any(w in q for w in ["timing", "timings", "opening", "closing", "close", "open today", "open", "hour", "hours", "when are you open", "what time", "when can i come", "visit your shop", "should i visit"]):
            intents.append("HOURS")

        # 4. Location & Address
        if any(w in q for w in ["where", "location", "address", "find you", "find the store", "find your store", "reach the shop", "reach you", "situated", "located", "where can i visit"]):
            intents.append("LOCATION")

        # 5. Contact & Phone
        if any(w in q for w in ["contact", "phone", "mobile", "number", "call", "whatsapp", "reach out"]):
            intents.append("CONTACT")

        # 6. Delivery
        if any(w in q for w in ["deliver", "delivery", "home delivery", "door delivery", "bring to my house", "bring my order to my house", "bring orders to my home"]):
            intents.append("DELIVERY")

        # 7. Pickup
        if any(w in q for w in ["pickup", "pick up", "pick-up", "collect", "takeaway", "take away", "counter"]) or bool(re.search(r"\b(pin|late|delay)\b", q)):
            intents.append("PICKUP")

        # 8. Payment
        if any(w in q for w in ["payment", "upi", "cash", "advance payment", "how do i pay", "how to pay", "accept payment"]) or bool(re.search(r"\bpay\b", q)):
            intents.append("PAYMENT")

        # 9. Cancellation & Refund
        if "cancel" in q or "cancellation" in q:
            intents.append("CANCELLATION")
        if "refund" in q:
            intents.append("REFUND")

        # 10. Ingredients & Allergens
        if "ingredient" in q or "ingredients" in q:
            intents.append("INGREDIENTS")
        if any(w in q for w in ["allergen", "allergens", "eggless", "nut", "gluten", "dairy", "milk"]) or re.search(r"\begg(s)?\b", q):
            intents.append("ALLERGENS")

        # 11. Customization, Sauces & Toppings
        if any(w in q for w in ["custom", "customise", "customize", "customization", "topping", "toppings", "sauce", "sauces", "filling", "fillings", "flavour", "flavors", "flavours", "flavor", "on top", "add on"]):
            intents.append("CUSTOMIZATION")

        # 12. Business Identity / Shop Name / Overview
        if any(k in q for k in [
            "what is dd house", "tell me about dd house", "tell me about your store",
            "what is the shop name", "name of the shop", "what is dd house kkd",
            "what is the store", "about dd house", "first time", "what should i know"
        ]) or re.search(r"\b(who|what)\s+is\s+dd\s*house\b", q):
            intents.append("BUSINESS")

        # 13. Product & Menu
        if any(w in q for w in [
            "cake", "cakes", "cake bowl", "cake bowls", "bowl", "bowls", "brownie", "brownies",
            "lollipop", "lollipops", "chocolate", "choco", "double chocolate", "triple chocolate",
            "choco truffle", "nutella", "oreo", "vanilla", "butterscotch", "product", "products",
            "menu", "catalogue", "catalog", "sweet", "sweets", "craving", "recommend", "dessert", "desserts"
        ]):
            intents.append("PRODUCT")

        # 14. Ordering
        if any(w in q for w in ["order", "ordering", "place an order", "pre-book", "prebook", "prep time"]):
            if "DELIVERY" not in intents and "PICKUP" not in intents:
                intents.append("ORDERING")

        # Fallbacks
        if not intents:
            if "dd house" in q or "shop" in q or "store" in q:
                intents.append("BUSINESS")
            else:
                intents.append("GENERAL")

        # Remove duplicates while preserving order
        unique_intents = []
        for it in intents:
            if it not in unique_intents:
                unique_intents.append(it)

        return unique_intents

    @staticmethod
    def get_intent_string(query: str) -> str:
        """Return formatted intent string for diagnostics and logging."""
        intents = IntentDetector.detect_intents(query)
        return ", ".join(intents)
