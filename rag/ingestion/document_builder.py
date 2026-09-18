"""Document builder: Compiles structured JSON records into human-readable markdown documents.
Ensures that when business data updates, documents stay synchronized.
"""
from pathlib import Path
from typing import Dict, List, Any
from rag.ingestion.loader import DataLoader
from rag.config import settings

class DocumentBuilder:
    def __init__(self, data_loader: DataLoader = None, output_dir: Path = None):
        self.loader = data_loader or DataLoader()
        self.output_dir = output_dir or settings.DOCUMENTS_DIR

    def build_all(self):
        """Build/rebuild markdown documents from structured data."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        records = self.loader.load_all_json_records()
        self._build_business_doc(records)
        self._build_products_doc(records)
        self._build_customization_doc(records)
        self._build_ordering_doc(records)
        self._build_payment_doc(records)
        self._build_policies_doc(records)
        self._build_pickup_doc(records)
        self._build_faq_doc(records)

    def _build_business_doc(self, records: List[Dict[str, Any]]):
        content = [
            "# DD House — Business Information\n",
            "DD House is a cake and food store located in Kakinada, Andhra Pradesh.\n",
            "## Store Location & Address",
            "DD House is located at: Venkat Nagar, Jayendra Nagar, Siddartha Nagar, Kakinada, Andhra Pradesh – 533003.\n",
            "## Operating Hours",
            "DD House is open every day (Monday to Sunday).",
            "Opening time: 4:00 PM",
            "Closing time: 11:00 PM\n",
            "## Contact Information",
            "Contact number: 7013522727",
            "WhatsApp number: 7013522727 (Available for contact and inquiries only, not for ordering).\n",
            "## Parking Information",
            "DD House does not have dedicated parking.",
            "Customers may use DMart parking as friendly parking advice.",
            "## Social Media & Online Links",
            "Official Instagram: https://www.instagram.com/ddhousekkd/\n",
            "## Detailed Business Attributes"
        ]
        for r in records:
            if r.get("category") in {"business", "social"} and r.get("verified"):
                val = r.get("value", {})
                if isinstance(val, dict):
                    for k, v in val.items():
                        content.append(f"- **{r.get('name')} ({k})**: {v}")
                else:
                    content.append(f"- **{r.get('name')}**: {val}")
        (self.output_dir / "business.md").write_text("\n".join(content), encoding="utf-8")

    def _build_products_doc(self, records: List[Dict[str, Any]]):
        content = [
            "# DD House — Menu & Products\n",
            "DD House sells delicious Cake Bowls, Brownies, and Cake Lollipops in Kakinada. All currently listed products are available every day.\n",
            "## Product Catalogue Overview",
            "- **Cake Bowls (₹89 - ₹99)**: Chocolate Cake Bowl (₹89), Double Chocolate (₹89), Triple Chocolate (₹99), Choco Truffle (₹99), Nutella (₹89), Oreo (₹89), Vanilla (₹89), Butterscotch (₹89).",
            "- **Brownies (₹50)**: Chocolate Brownie (₹50), Choco-Chip Brownie (₹50). (Note: Brownies cannot be customized).",
            "- **Cake Lollipops (₹30)**: Chocolate Lollipop (₹30), Vanilla Lollipop (₹30). (Cheapest items on the menu).\n",
            "## Detailed Product List\n",
            "| Product Name | Category | Price (INR) | Daily Available |",
            "| :--- | :--- | :--- | :--- |"
        ]
        for r in records:
            if r.get("category") == "product" and r.get("verified"):
                val = r.get("value", {})
                price = val.get("price", "N/A")
                pcat = r.get("product_category", "product")
                content.append(f"| {r.get('name')} | {pcat} | ₹{price} | Yes |")
        (self.output_dir / "products.md").write_text("\n".join(content), encoding="utf-8")

    def _build_customization_doc(self, records: List[Dict[str, Any]]):
        content = ["# DD House — Customization\n"]
        for r in records:
            if r.get("category") == "customization":
                content.append(f"### {r.get('name')}")
                val = r.get("value")
                if isinstance(val, dict):
                    for k, v in val.items():
                        content.append(f"- {k}: {v}")
                elif val is None and r.get("status") == "TBD":
                    content.append(f"- Status: TBD (Customization costs extra, exact pricing TBD)")
                content.append("")
        (self.output_dir / "customization.md").write_text("\n".join(content), encoding="utf-8")

    def _build_ordering_doc(self, records: List[Dict[str, Any]]):
        content = ["# DD House — Ordering Policies\n"]
        for r in records:
            if r.get("category") == "ordering" and r.get("verified"):
                val = r.get("value", {})
                statement = val.get("statement") if isinstance(val, dict) else str(val)
                content.append(f"- **{r.get('name')}**: {statement}")
        (self.output_dir / "ordering.md").write_text("\n".join(content), encoding="utf-8")

    def _build_payment_doc(self, records: List[Dict[str, Any]]):
        content = ["# DD House — Payment\n"]
        for r in records:
            if r.get("category") == "payment" and r.get("verified"):
                val = r.get("value", {})
                statement = val.get("statement") if isinstance(val, dict) else str(val)
                content.append(f"- **{r.get('name')}**: {statement}")
        (self.output_dir / "payment.md").write_text("\n".join(content), encoding="utf-8")

    def _build_policies_doc(self, records: List[Dict[str, Any]]):
        content = ["# DD House — Policies & TBD Records\n"]
        for r in records:
            if r.get("category") in {"cancellation_refund", "allergen", "ingredient"}:
                val = r.get("value")
                stmt = r.get("statement") or (val.get("statement") if isinstance(val, dict) else str(val))
                content.append(f"- **{r.get('name')}** (Verified: {r.get('verified')}): {stmt or 'TBD'}")
        (self.output_dir / "policies.md").write_text("\n".join(content), encoding="utf-8")

    def _build_pickup_doc(self, records: List[Dict[str, Any]]):
        content = ["# DD House — Pickup\n"]
        for r in records:
            if r.get("category") == "pickup":
                val = r.get("value")
                stmt = r.get("statement") or (val.get("statement") if isinstance(val, dict) else str(val))
                content.append(f"- **{r.get('name')}**: {stmt}")
        (self.output_dir / "pickup.md").write_text("\n".join(content), encoding="utf-8")

    def _build_faq_doc(self, records: List[Dict[str, Any]]):
        content = ["# DD House — FAQ\n"]
        for r in records:
            if r.get("category") == "faq":
                val = r.get("value", {})
                content.append(f"**Q: {val.get('question')}**\nA: {val.get('answer')}\n")
        (self.output_dir / "faq.md").write_text("\n".join(content), encoding="utf-8")
