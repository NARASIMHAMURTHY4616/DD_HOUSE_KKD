"""Metadata filter for query routing and chunk filtering.
"""
import re
from typing import Dict, Any, Optional, Callable
from rag.ingestion.chunker import DocumentChunk

class MetadataFilter:
    @staticmethod
    def extract_query_hints(query: str) -> Dict[str, Any]:
        """Analyze query to determine likely category, product, and policy targets."""
        q = query.lower()
        hints: Dict[str, Any] = {
            "target_category": None,
            "target_product": None,
            "target_product_category": None,
            "target_policy": None
        }

        # Product category detection
        if "brownie" in q:
            hints["target_product_category"] = "brownie"
        elif "lollipop" in q:
            hints["target_product_category"] = "cake_lollipop"
        elif "cake bowl" in q or "bowl" in q or "cake" in q or "cakes" in q:
            hints["target_product_category"] = "cake_bowl"

        # Specific product name detection (exact or word boundary)
        products = [
            ("triple chocolate", "Triple Chocolate"),
            ("double chocolate", "Double Chocolate"),
            ("choco truffle", "Choco Truffle"),
            ("chocolate cake bowl", "Chocolate Cake Bowl"),
            ("nutella", "Nutella"),
            ("oreo", "Oreo"),
            ("butterscotch", "Butterscotch"),
            ("vanilla lollipop", "Vanilla Lollipop"),
            ("chocolate lollipop", "Chocolate Lollipop"),
            ("choco-chip brownie", "Choco-Chip Brownie"),
            ("choco chip brownie", "Choco-Chip Brownie"),
            ("chocolate brownie", "Chocolate Brownie"),
        ]
        is_broad_catalogue = any(k in q for k in [
            "what products", "what are the products", "which products", "products does",
            "products did", "what do you sell", "what did dd sell", "what does dd sell",
            "menu", "catalogue", "catalog", "all items", "what items", "what can i order"
        ])
        if not is_broad_catalogue:
            for term, formal_name in products:
                if re.search(rf"\b{re.escape(term)}\b", q):
                    hints["target_product"] = formal_name
                    break
            # Check standalone vanilla only if not vanilla lollipop
            if not hints["target_product"] and re.search(r"\bvanilla\b", q) and "lollipop" not in q:
                hints["target_product"] = "Vanilla"

        # Category detection
        if any(k in q for k in ["customize", "customization", "filling", "topping", "sauce", "drizzle", "flavour", "flavor", "write my name", "message", "theme"]):
            hints["target_category"] = "customization"
        elif any(k in q for k in ["product", "products", "sell", "sells", "menu", "item", "items", "price", "cost", "how much", "rate", "cheapest", "available every day"]):
            hints["target_category"] = "product"
        elif any(k in q for k in ["what is dd house", "about dd house", "open", "close", "hour", "hours", "timing", "timings", "phone", "contact", "number", "address", "where", "location", "parking", "dmart", "sunday", "store"]):
            hints["target_category"] = "business"
        elif any(k in q for k in ["cancel", "refund"]):
            hints["target_category"] = "cancellation_refund"
        elif any(k in q for k in ["deliver", "delivery", "order", "whatsapp", "pre-book", "prebook", "prep", "preparation"]):
            hints["target_category"] = "ordering"
        elif any(k in q for k in ["upi", "cash", "advance payment"]) or re.search(r"\b(pay|payment)\b", q):
            hints["target_category"] = "payment"
        elif any(k in q for k in ["pickup", "collect"]) or re.search(r"\b(late|delay|delayed|pin)\b", q):
            hints["target_category"] = "pickup"
        elif any(k in q for k in ["eggless", "allergen", "ingredient", "calorie", "gluten", "nut", "dairy", "milk"]) or re.search(r"\begg(s)?\b", q):
            hints["target_category"] = "allergen"

        return hints

    @staticmethod
    def build_filter(hints: Dict[str, Any]) -> Optional[Callable[[DocumentChunk], bool]]:
        """Build a predicate filter function from hints, or None if broad search is desired."""
        target_product = hints.get("target_product")
        target_prod_cat = hints.get("target_product_category")
        target_cat = hints.get("target_category")

        # For strict customization brownie queries:
        if target_cat == "customization" and target_prod_cat == "brownie":
            return lambda c: (c.category == "customization" and (c.product_category == "brownie" or "brownie" in c.text.lower()))

        # For specific product pricing
        if target_cat == "product" and target_product:
            return lambda c: (c.product == target_product or target_product.lower() in c.text.lower())

        return None
