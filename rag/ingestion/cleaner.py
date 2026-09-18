"""Text cleaner and normalizer for RAG queries and documents.
"""
import re

class TextCleaner:
    @staticmethod
    def clean_text(text: str) -> str:
        """Collapse whitespace and strip leading/trailing spaces."""
        if not text:
            return ""
        # Replace multiple spaces/newlines with single space
        cleaned = re.sub(r"\s+", " ", text)
        return cleaned.strip()

    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize user query for enhanced retrieval matching."""
        if not query:
            return ""
        q = query.strip()
        
        # Normalize rupees representations
        q = re.sub(r"(?i)\brs\.?\s*", "₹", q)
        q = re.sub(r"(?i)\brupees\b", "₹", q)

        # Normalize DD House shop entity variations
        q = re.sub(r"(?i)\b(ddhousekkd|dd_house_kkd|ddhouse_kkd|dd\s+house\s+kkd|ddhouse\s+kkd)\b", "DD House KKD", q)
        q = re.sub(r"(?i)\b(ddhouse|dd_house|dd\s+house\s+kakinada|ddhouse\s+kakinada)\b", "DD House", q)
        q = re.sub(r"(?i)\b(the\s+shop|your\s+shop|the\s+store|your\s+store|the\s+bakery|the\s+dessert\s+shop)\b", "DD House", q)

        # Normalize common typo / shorthand variations for retrieval
        q = re.sub(r"(?i)\b(cake|cakes|caek|caeks|cakke|cakk|cke|ckear|ckae|cak|ceak|caks)\b", "cake", q)
        q = re.sub(r"(?i)\b(cake\s*bowl|cake\s*bowls|cakebowl|cakebowls|caek\s*bowl|caek\s*bowls|cakk\s*bowl|cakk\s*bowls)\b", "cake bowl", q)
        q = re.sub(r"(?i)\b(choco|chocoo|choc|choclate|chocolatee|chocolet|chocalate|choclat|chocol|choclates|chocolates|chocolatey|chocolaty|choclatey)\b", "chocolate", q)
        q = re.sub(r"(?i)\b(browny|brwine|brwnie|browniee|brownee|brownys|brownies|browni)\b", "brownie", q)
        q = re.sub(r"(?i)\b(sause|sauuce|saucee|soupe|soupes|sauce|sauces|saucss)\b", "sauces", q)
        q = re.sub(r"(?i)\b(toppng|toppngs|toping|topings|topping|toppings)\b", "toppings", q)
        q = re.sub(r"(?i)\b(flavor|flavors|flavour|flavours|flaver|flavers)\b", "flavour", q)
        q = re.sub(r"(?i)\b(customize|customise|customiz|customisation|customizations|customizing)\b", "customization", q)
        q = re.sub(r"(?i)\b(deliver|delivr|delivry|delvery|delivering|deliveries|delivery)\b", "delivery", q)
        q = re.sub(r"(?i)\b(lollipop|lollipops|lolipop|lolipops|lollypop|lollypops|lolli|lolly)\b", "cake lollipop", q)
        q = re.sub(r"(?i)\b(vanilla|vanila|vanilaa|vanillla)\b", "vanilla", q)
        q = re.sub(r"(?i)\b(social-media|social\s+media|social\s+links?|sociallinks?|instagram\s+handle|instagram\s+link|find\s+online)\b", "social media instagram", q)
        q = re.sub(r"(?i)\b(timing|timings|opening\s+time|closing\s+time|opening\s+hours|business\s+hours|operating\s+hours|open\s+timing|open\s+time|close\s+time)\b", "operating hours timings", q)
        q = re.sub(r"(?i)\b(phone\s+number|contact\s+number|mobile\s+number|call\s+number|phone|contact)\b", "phone number contact", q)
        q = re.sub(r"(?i)\b(address|adress|addres|location|locaton|loctn|where\s+are\s+you)\b", "address location", q)
        q = re.sub(r"(?i)\b(cancel\s+my\s+order|cancel\s+order|cancellation\s+policy|refund\s+policy|how\s+to\s+cancel)\b", "cancellation refund policy", q)
        q = re.sub(r"(?i)\b(how\s+to\s+pay|how\s+do\s+i\s+pay|payment\s+methods?|payment\s+options?|accept\s+payment)\b", "payment methods upi cash", q)
        q = re.sub(r"(?i)\b(pickup|pick\s+up|pick-up|take\s+away|store\s+pickup)\b", "store pickup", q)
        q = re.sub(r"(?i)\b(bring\s+to\s+my\s+house|bring\s+to\s+my\s+home|home\s+delivery|door\s+delivery)\b", "home delivery", q)
        q = re.sub(r"(?i)\bdouble choco\b", "double chocolate", q)
        q = re.sub(r"(?i)\bdouble choc\b", "double chocolate", q)
        q = re.sub(r"(?i)\btriple choco\b", "triple chocolate", q)
        q = re.sub(r"(?i)\btriple choc\b", "triple chocolate", q)
        q = re.sub(r"(?i)\bdd home\b", "DD House home delivery", q)
        q = re.sub(r"(?i)\bproducts?\s+did\s+dd\s+sells?\b", "products does DD House sell", q)
        q = re.sub(r"(?i)\bdid\s+dd\s+sells?\b", "does DD House sell", q)
        q = re.sub(r"(?i)\bwhat\s+did\s+dd\s+sell\b", "what does DD House sell", q)
        q = re.sub(r"(?i)\bdo\s+you\s+sells?\b", "do you sell", q)

        # Collapse multiple spaces
        q = re.sub(r"\s+", " ", q)
        return q.strip()

clean_query = TextCleaner.normalize_query
