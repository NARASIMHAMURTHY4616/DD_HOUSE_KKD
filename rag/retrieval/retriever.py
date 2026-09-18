"""Retriever implementation with hybrid scoring, metadata routing, confidence calibration,
and two-stage candidate filtering.
"""
from typing import List, Tuple, Dict, Any, Optional
import re
from rag.config import settings
from rag.ingestion.chunker import DocumentChunk
from rag.ingestion.cleaner import TextCleaner
from rag.retrieval.vector_store import VectorStore
from rag.retrieval.metadata_filter import MetadataFilter

from rag.retrieval.intent_detector import IntentDetector

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "can", "could", "would", "should", "shall", "may", "might",
    "i", "you", "we", "they", "he", "she", "it", "me", "my", "your", "our",
    "what", "when", "where", "how", "why", "which", "who", "whom",
    "at", "in", "on", "to", "for", "of", "with", "by", "from", "up", "about", "into",
    "there", "have", "has", "had", "get", "take", "make", "tell", "much", "want",
    "looking", "something", "options", "different", "types", "choose", "recommend"
}

FOREIGN_CONCEPTS = [
    "hyderabad", "vijayawada", "bangalore", "2 kg", "2kg", "wedding cake",
    "wedding cakes", "loyalty program", "calories", "calorie count", "birthday cake",
    "japan", "tokyo", "weather", "delhi", "mumbai", "prime minister", "president",
    "joke", "stock market"
]

class Retriever:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()
        self.cleaner = TextCleaner()

    def retrieve_with_diagnostics(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """Retrieve candidates, evaluate relevance, perform two-stage filtering, and return diagnostics."""
        k = top_k or settings.TOP_K
        clean_q = self.cleaner.normalize_query(query)
        lower_q = clean_q.lower()
        hints = MetadataFilter.extract_query_hints(clean_q)
        intents = IntentDetector.detect_intents(lower_q)
        intent_str = ", ".join(intents)

        # 1. Check for foreign/out-of-scope concepts
        is_foreign = "UNKNOWN" in intents or any(fc in lower_q for fc in FOREIGN_CONCEPTS)

        # 2. Extract content query tokens
        raw_tokens = re.findall(r"\b\w+\b", lower_q)
        query_tokens = [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 1]

        # 3. Search vector store across all knowledge chunks
        all_chunk_count = len(self.vector_store.chunks) if self.vector_store.chunks else 80
        results = self.vector_store.search(clean_q, top_k=all_chunk_count, filter_fn=None)

        if not results:
            return {
                "clean_query": clean_q,
                "detected_intent": intent_str,
                "candidates": [],
                "accepted": [],
                "rejected": [],
                "verified_sent": []
            }

        scored_results: List[Tuple[DocumentChunk, float, str]] = []

        for chunk, cosine_sim in results:
            c_text = (chunk.text + " " + chunk.category + " " + (chunk.product or "") + " " + (chunk.policy or "")).lower()

            # If question has foreign concept completely absent from DD House
            if is_foreign:
                scored_results.append((chunk, 0.20, "Out of scope"))
                continue

            # Calculate token recall
            if query_tokens:
                matched = 0
                for tok in query_tokens:
                    if tok in c_text or (len(tok) > 3 and tok[:4] in c_text):
                        matched += 1
                token_recall = matched / len(query_tokens)
            else:
                token_recall = 0.0

            # Base hybrid score combined from dense cosine and token recall
            score = 0.45 * min(1.0, max(0.0, float(cosine_sim)) * 2.5) + 0.55 * token_recall
            relevance_reason = "Semantic similarity"

            # Targeted intent calibrations:
            target_product = hints.get("target_product")
            if target_product and chunk.product == target_product:
                if chunk.category == "product":
                    score = max(score, 0.95)
                    relevance_reason = f"Product match: {target_product}"
                elif any(w in lower_q for w in ["eggless", "ingredient", "allergen", "nut", "milk"]) or re.search(r"\begg(s)?\b", lower_q):
                    score = max(score, 0.94)
                    relevance_reason = f"Product allergen/ingredient: {target_product}"
                else:
                    score = max(score, 0.70)

            # Chocolate intent
            if "PRODUCT" in intents and any(w in lower_q for w in ["chocolate", "choco"]):
                if chunk.product in {"Chocolate Cake Bowl", "Double Chocolate", "Triple Chocolate", "Choco Truffle", "Chocolate Brownie", "Chocolate Lollipop"}:
                    score = max(score, 0.94)
                    relevance_reason = "Chocolate product match"
                elif chunk.policy == "product_catalogue":
                    score = max(score, 0.93)
                elif chunk.policy in {"menu_cake_bowls", "menu_brownies", "menu_lollipops"}:
                    score = max(score, 0.92)
                elif chunk.policy == "sauces":
                    score = max(score, 0.88)

            # Brownie intent
            if "PRODUCT" in intents and "brownie" in lower_q:
                if chunk.policy == "menu_brownies":
                    score = max(score, 0.96)
                    relevance_reason = "Brownie menu match"
                elif chunk.product in {"Chocolate Brownie", "Choco-Chip Brownie"}:
                    score = max(score, 0.95)
                    relevance_reason = "Brownie product match"
                elif chunk.product_category == "brownie" and chunk.category == "product":
                    score = max(score, 0.94)
                elif chunk.policy == "product_catalogue":
                    score = max(score, 0.90)

            # Cake bowls / lollipops / products
            if "PRODUCT" in intents:
                if "cake" in lower_q or "bowl" in lower_q:
                    if chunk.policy == "menu_cake_bowls":
                        score = max(score, 0.96)
                        relevance_reason = "Cake bowl menu match"
                    elif chunk.product_category == "cake_bowl" and chunk.category == "product":
                        score = max(score, 0.94)
                    elif chunk.policy == "product_catalogue":
                        score = max(score, 0.92)
                if "lollipop" in lower_q or "lollipops" in lower_q:
                    if chunk.policy == "menu_lollipops":
                        score = max(score, 0.96)
                        relevance_reason = "Lollipop menu match"
                    elif chunk.product_category == "cake_lollipop" and chunk.category == "product":
                        score = max(score, 0.93)
                if any(w in lower_q for w in ["menu", "catalogue", "what products", "what items", "what can i order", "recommend", "sweet", "craving", "dessert"]):
                    if chunk.policy == "product_catalogue":
                        score = max(score, 0.98)
                        relevance_reason = "Product catalogue match"
                    elif chunk.policy in {"menu_cake_bowls", "menu_brownies", "menu_lollipops"}:
                        score = max(score, 0.94)

            # Customization intent
            if "CUSTOMIZATION" in intents:
                if any(w in lower_q for w in ["sauce", "sauces", "drizzle", "drizzles"]):
                    if chunk.policy == "sauces":
                        score = max(score, 0.96)
                        relevance_reason = "Sauces customization match"
                    elif chunk.category == "customization":
                        score = max(score, 0.92)
                elif any(w in lower_q for w in ["filling", "fillings"]):
                    if chunk.policy == "fillings":
                        score = max(score, 0.96)
                        relevance_reason = "Fillings customization match"
                elif any(w in lower_q for w in ["topping", "toppings", "on top", "add on"]):
                    if chunk.policy == "toppings":
                        score = max(score, 0.96)
                        relevance_reason = "Toppings customization match"
                    elif chunk.policy in {"flavours", "sauces", "fillings"}:
                        score = max(score, 0.92)
                elif "brownie" in lower_q:
                    if chunk.policy in {"brownie_customization", "no_customization"}:
                        score = max(score, 0.96)
                        relevance_reason = "Brownie customization rule"
                else:
                    if chunk.policy == "customization_eligibility":
                        score = max(score, 0.96)
                        relevance_reason = "Customization eligibility match"
                    elif chunk.category == "customization":
                        score = max(score, 0.92)

            # Business Overview & Identity
            if "BUSINESS" in intents:
                if chunk.policy == "business_overview":
                    score = max(score, 0.98)
                    relevance_reason = "Business overview match"
                elif chunk.policy in {"business_name", "business_type"}:
                    score = max(score, 0.96)
                    relevance_reason = "Business info match"
                elif chunk.policy in {"location", "operating_hours"}:
                    score = max(score, 0.92)

            # Location & Address
            if "LOCATION" in intents:
                if chunk.policy == "location":
                    score = max(score, 0.98)
                    relevance_reason = "Location & address match"
                elif chunk.policy == "pickup_location":
                    score = max(score, 0.94)
                elif chunk.policy == "business_overview":
                    score = max(score, 0.92)

            # Operating Hours & Timings
            if "HOURS" in intents:
                if chunk.policy == "operating_hours":
                    score = max(score, 0.98)
                    relevance_reason = "Operating hours match"
                elif chunk.policy == "faq" and "hours" in chunk.text.lower():
                    score = max(score, 0.94)
                elif chunk.policy == "business_overview":
                    score = max(score, 0.90)

            # Contact & Phone
            if "CONTACT" in intents:
                if chunk.policy in {"contact_phone", "contact_whatsapp"}:
                    score = max(score, 0.98)
                    relevance_reason = "Contact & phone match"
                elif chunk.policy == "business_overview":
                    score = max(score, 0.90)

            # Delivery & Pickup
            if "DELIVERY" in intents:
                if chunk.policy == "delivery_policy":
                    score = max(score, 0.98)
                    relevance_reason = "Delivery policy match"
                elif chunk.category == "faq" and "delivery" in chunk.text.lower():
                    score = max(score, 0.95)

            if "PICKUP" in intents:
                if chunk.policy in {"pickup_location", "delivery_policy"}:
                    score = max(score, 0.96)
                    relevance_reason = "Pickup policy match"
                elif chunk.policy in {"order_pin_verification", "delay_handling", "pickup_time_selection"}:
                    score = max(score, 0.93)

            # Payment
            if "PAYMENT" in intents:
                if chunk.policy in {"upi_payment", "cash_payment", "advance_payment"}:
                    score = max(score, 0.96)
                    relevance_reason = "Payment methods match"
                elif chunk.category == "payment":
                    score = max(score, 0.92)

            # Cancellation & Refund
            if "CANCELLATION" in intents or "REFUND" in intents:
                if chunk.policy in {"cancellation_within_5_min", "cancellation_after_5_min"}:
                    score = max(score, 0.96)
                    relevance_reason = "Cancellation/refund policy match"
                elif chunk.category == "cancellation_refund" or (chunk.category == "faq" and "cancellation" in chunk.text.lower()):
                    score = max(score, 0.92)

            # Social Links
            if "SOCIAL" in intents:
                if chunk.category == "social" or chunk.policy == "social_links":
                    score = max(score, 0.98)
                    relevance_reason = "Social links match"
                elif chunk.policy == "business_overview":
                    score = max(score, 0.92)

            # Ordering
            if "ORDERING" in intents:
                if chunk.policy in {"website_ordering", "same_day_orders", "pre_booking", "preparation_time"}:
                    score = max(score, 0.94)
                    relevance_reason = "Ordering policy match"
                elif chunk.category == "ordering":
                    score = max(score, 0.90)

            # Allergens & Ingredients
            if "ALLERGENS" in intents or "INGREDIENTS" in intents:
                if chunk.category in {"allergen", "ingredient"}:
                    score = max(score, 0.85)
                    relevance_reason = "Allergen/ingredient policy"

            scored_results.append((chunk, round(score, 4), relevance_reason))

        # Sort all candidates by score descending (verified chunks prioritized on tied scores)
        scored_results.sort(key=lambda x: (x[1], 1 if x[0].verified else 0), reverse=True)

        candidate_window = scored_results[: settings.VECTOR_CANDIDATE_K]
        accepted = [
            (chunk, score, reason) for chunk, score, reason in candidate_window
            if chunk.verified and score >= settings.SIMILARITY_THRESHOLD
        ]
        rejected = [
            (chunk, score, reason) for chunk, score, reason in candidate_window
            if (not chunk.verified) or score < settings.SIMILARITY_THRESHOLD
        ]

        # Verified context sent to LLM
        verified_sent = [(chunk, score) for chunk, score, _ in accepted[:k]]

        return {
            "clean_query": clean_q,
            "detected_intent": intent_str,
            "candidates": candidate_window,
            "accepted": accepted,
            "rejected": rejected,
            "verified_sent": verified_sent
        }

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        apply_filter: bool = True
    ) -> List[Tuple[DocumentChunk, float]]:
        """Retrieve top verified document chunks for a query."""
        diag = self.retrieve_with_diagnostics(query, top_k=top_k)
        return diag["verified_sent"]
