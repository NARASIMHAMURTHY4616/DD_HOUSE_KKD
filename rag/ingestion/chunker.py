"""Semantic chunker creating high-precision, atomic chunks with rich metadata.
"""
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    category: str
    source_type: str
    verified: bool
    product: str = ""
    product_category: str = ""
    policy: str = ""
    last_updated: str = "2026-09-18"
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class SemanticChunker:
    def chunk_records(self, records: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """Convert structured records into focused semantic chunks with metadata."""
        chunks: List[DocumentChunk] = []

        for r in records:
            cat = r.get("category", "")
            rec_id = r.get("id", "")
            source_type = r.get("source_type", "business_provided")
            verified = r.get("verified", False)
            status = r.get("status", "active")
            last_updated = r.get("last_updated", "2026-09-18")
            val = r.get("value")

            if cat == "product":
                name = r.get("name", "")
                pcat = r.get("product_category", "product")
                price = val.get("price") if isinstance(val, dict) else None
                customizable = val.get("customizable", True if pcat == "cake_bowl" else False) if isinstance(val, dict) else False

                # Primary price and availability chunk
                if price is not None:
                    txt = f"{name} is a {pcat} sold by DD House. It costs ₹{price} and is available every day."
                    chunks.append(DocumentChunk(
                        chunk_id=f"chunk_{rec_id}_price",
                        text=txt,
                        category="product",
                        source_type=source_type,
                        verified=verified,
                        product=name,
                        product_category=pcat,
                        policy="pricing",
                        last_updated=last_updated,
                        status=status
                    ))

                # Special rule chunk for brownies
                if pcat == "brownie":
                    chunks.append(DocumentChunk(
                        chunk_id=f"chunk_{rec_id}_custom",
                        text=f"{name} cannot be customized. Brownies at DD House are not eligible for customization.",
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        product=name,
                        product_category="brownie",
                        policy="no_customization",
                        last_updated=last_updated,
                        status=status
                    ))

            elif cat == "business":
                name = r.get("name", "")
                if rec_id == "business_name":
                    txt = "Official shop name is DD House (also known as DD House KKD, DD House Kakinada). DD House is a bakery and cake/food store in Kakinada."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_business_name",
                        text=txt,
                        category="business",
                        source_type=source_type,
                        verified=verified,
                        policy="business_name",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "business_type":
                    txt = "DD House (DD HOUSE KKD) is a cake, bakery and food store specializing in delicious cake bowls, brownies, and cake lollipops in Kakinada."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_business_type",
                        text=txt,
                        category="business",
                        source_type=source_type,
                        verified=verified,
                        policy="business_type",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "business_hours":
                    opening = val.get("opening", "4:00 PM") if isinstance(val, dict) else "4:00 PM"
                    closing = val.get("closing", "11:00 PM") if isinstance(val, dict) else "11:00 PM"
                    txt = f"DD House operating hours and timings: DD House is open every day (Monday to Sunday) from {opening} to {closing}. We are open today from 4:00 PM to 11:00 PM. Opening time is 4:00 PM and closing time is 11:00 PM."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_business_hours",
                        text=txt,
                        category="business",
                        source_type=source_type,
                        verified=verified,
                        policy="operating_hours",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "business_location":
                    addr = val.get("address", "") if isinstance(val, dict) else str(val)
                    txt = f"DD House store location and address: DD House is located at {addr}. You can visit and find the shop at Venkat Nagar, Jayendra Nagar, Siddartha Nagar, Kakinada, Andhra Pradesh – 533003."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_business_location",
                        text=txt,
                        category="business",
                        source_type=source_type,
                        verified=verified,
                        policy="location",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "business_contact_phone":
                    phone = val.get("phone", "7013522727") if isinstance(val, dict) else str(val)
                    txt = f"DD House contact phone number: You can contact DD House by calling {phone}."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_business_phone",
                        text=txt,
                        category="business",
                        source_type=source_type,
                        verified=verified,
                        policy="contact_phone",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "business_contact_whatsapp":
                    whatsapp = val.get("whatsapp", "7013522727") if isinstance(val, dict) else "7013522727"
                    txt = f"DD House WhatsApp contact number is {whatsapp} for inquiries and customer support only. Note that WhatsApp cannot be used to place orders."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_business_whatsapp",
                        text=txt,
                        category="business",
                        source_type=source_type,
                        verified=verified,
                        policy="contact_whatsapp",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "business_parking":
                    txt = "DD House does not have dedicated parking. Customers may use DMart parking as friendly parking advice. IMPORTANT: DMart parking is NOT an official DD House parking facility."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_business_parking",
                        text=txt,
                        category="business",
                        source_type=source_type,
                        verified=verified,
                        policy="parking",
                        last_updated=last_updated,
                        status=status
                    ))

            elif cat == "customization":
                name = r.get("name", "")
                if rec_id == "customization_cake_bowl_eligibility":
                    txt = "Cake bowls can be customized with flavours, fillings, toppings and sauces. Brownies cannot be customized."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_general",
                        text=txt,
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        product_category="cake_bowl",
                        policy="customization_eligibility",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "customization_flavours":
                    opts = ", ".join(val.get("options", []))
                    txt = f"Available customization flavours for cake bowls: {opts}."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_flavours",
                        text=txt,
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        product_category="cake_bowl",
                        policy="flavours",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "customization_fillings":
                    opts = ", ".join(val.get("options", []))
                    txt = f"Available customization fillings for cake bowls: {opts}."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_fillings",
                        text=txt,
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        product_category="cake_bowl",
                        policy="fillings",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "customization_toppings":
                    opts = ", ".join(val.get("options", []))
                    txt = f"Available customization toppings for cake bowls: {opts}."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_toppings",
                        text=txt,
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        product_category="cake_bowl",
                        policy="toppings",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "customization_sauces_drizzles":
                    opts = ", ".join(val.get("options", []))
                    txt = f"Available customization sauces and drizzles for cake bowls: {opts}."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_sauces",
                        text=txt,
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        product_category="cake_bowl",
                        policy="sauces",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "customization_name_message":
                    txt = "Customer can request a name and message. The name or message is NOT written directly on the cake. The name/message can be written on the BOX."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_message",
                        text=txt,
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        policy="name_message_box",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "customization_custom_themes":
                    txt = "There is NO custom cake design or theme service in the verified DD House project data. We do not provide themed or shaped custom cakes."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_no_themes",
                        text=txt,
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        policy="custom_cake_themes",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "customization_brownie_eligibility":
                    txt = "Brownies cannot be customized. No flavours, toppings, or fillings can be added to brownies."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_brownie_denied",
                        text=txt,
                        category="customization",
                        source_type=source_type,
                        verified=verified,
                        product_category="brownie",
                        policy="brownie_customization",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "customization_pricing":
                    txt = "Customization costs extra. The exact customization pricing is UNKNOWN / TBD."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_customization_price_tbd",
                        text=txt,
                        category="customization",
                        source_type="unknown",
                        verified=False,
                        policy="customization_price",
                        last_updated=last_updated,
                        status="TBD"
                    ))

            elif cat == "ordering":
                if rec_id == "ordering_channels_website":
                    txt = "Online ordering is supported through the DD House website."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_website",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="website_ordering",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "ordering_channels_whatsapp":
                    txt = "Ordering through WhatsApp is NOT supported. WhatsApp is only for inquiries."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_whatsapp",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="no_whatsapp_ordering",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "ordering_channels_instagram":
                    txt = "Ordering through Instagram is NOT supported."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_instagram",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="no_instagram_ordering",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "ordering_multiple_products":
                    txt = "Customers can order multiple products in a single order."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_multi_product",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="multiple_products",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "ordering_pickup_time_selection":
                    txt = "Customers can select their preferred pickup time when placing an online order."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_pickup_time",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="pickup_time_selection",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "ordering_same_day":
                    txt = "Same-day orders are supported at DD House."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_same_day",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="same_day_orders",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "ordering_prebooking":
                    txt = "Pre-booking orders is supported. Customers can pre-book at least 4 hours in advance."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_prebooking",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="pre_booking",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "ordering_preparation_time":
                    txt = "Normal preparation takes 15 minutes. During heavy rush, preparation takes up to 20 minutes."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_prep_time",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="preparation_time",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "ordering_pickup_only_delivery":
                    txt = "DD House currently supports store pickup rather than delivery. Customers must pick up orders from the store. Home delivery is not provided."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_ordering_pickup_delivery",
                        text=txt,
                        category="ordering",
                        source_type=source_type,
                        verified=verified,
                        policy="delivery_policy",
                        last_updated=last_updated,
                        status=status
                    ))

            elif cat == "payment":
                if rec_id == "payment_methods_upi":
                    txt = "DD House accepts UPI payments."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_payment_upi",
                        text=txt,
                        category="payment",
                        source_type=source_type,
                        verified=verified,
                        policy="upi_payment",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "payment_methods_cash":
                    txt = "DD House accepts Cash payments."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_payment_cash",
                        text=txt,
                        category="payment",
                        source_type=source_type,
                        verified=verified,
                        policy="cash_payment",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "payment_advance_requirement":
                    txt = "Online orders require advance payment."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_payment_advance",
                        text=txt,
                        category="payment",
                        source_type=source_type,
                        verified=verified,
                        policy="advance_payment",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "payment_online_pricing":
                    txt = "Online product prices are the same as menu prices. There is no price difference."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_payment_pricing_parity",
                        text=txt,
                        category="payment",
                        source_type=source_type,
                        verified=verified,
                        policy="price_parity",
                        last_updated=last_updated,
                        status=status
                    ))

            elif cat == "cancellation_refund":
                if rec_id == "cancellation_within_5_minutes":
                    txt = "Customer can cancel an order within 5 minutes of placing it and receive a full refund."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_cancellation_5min",
                        text=txt,
                        category="cancellation_refund",
                        source_type=source_type,
                        verified=verified,
                        policy="cancellation_within_5_min",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "cancellation_after_5_minutes":
                    txt = "After 5 minutes, some amount will be charged and the remaining amount will be refunded depending on elapsed time and preparation status. There is no verified fixed percentage or fixed cancellation fee."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_cancellation_after_5min",
                        text=txt,
                        category="cancellation_refund",
                        source_type=source_type,
                        verified=verified,
                        policy="cancellation_after_5_min",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "cancellation_exact_fee":
                    txt = "There is NO verified fixed cancellation fee and NO verified fixed refund percentage. Exact refund calculation depends on elapsed time and preparation status."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_cancellation_no_fixed_fee",
                        text=txt,
                        category="cancellation_refund",
                        source_type="unknown",
                        verified=False,
                        policy="exact_cancellation_fee",
                        last_updated=last_updated,
                        status="TBD"
                    ))

            elif cat == "pickup":
                if rec_id == "pickup_location_mandatory":
                    txt = "Pickup occurs at the DD House store in Venkat Nagar, Kakinada. Customer must pick up the order."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_pickup_location",
                        text=txt,
                        category="pickup",
                        source_type=source_type,
                        verified=verified,
                        policy="pickup_location",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "pickup_order_verification":
                    txt = "When an order is placed, an Order ID and a PIN are generated. Customer must provide order identification details (Order ID and PIN) at the counter to collect the order."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_pickup_id_pin",
                        text=txt,
                        category="pickup",
                        source_type=source_type,
                        verified=verified,
                        policy="order_pin_verification",
                        last_updated=last_updated,
                        status=status
                    ))
                elif rec_id == "pickup_delay_handling":
                    txt = "If a customer is late and informs the store early about the delay, the store attempts to keep the item safe. If necessary and appropriate, a fresh item may be prepared when the customer arrives."
                    chunks.append(DocumentChunk(
                        chunk_id="chunk_pickup_delay",
                        text=txt,
                        category="pickup",
                        source_type=source_type,
                        verified=verified,
                        policy="delay_handling",
                        last_updated=last_updated,
                        status=status
                    ))

            elif cat == "faq":
                q = val.get("question", "")
                a = val.get("answer", "")
                txt = f"FAQ: {q} Answer: {a}"
                chunks.append(DocumentChunk(
                    chunk_id=f"chunk_faq_{rec_id}",
                    text=txt,
                    category="faq",
                    source_type=source_type,
                    verified=verified,
                    policy="faq",
                    last_updated=last_updated,
                    status=status
                ))

            elif cat == "social":
                url = val.get("url", "") if isinstance(val, dict) else str(val)
                platform = val.get("platform", "Instagram") if isinstance(val, dict) else "Instagram"
                txt = f"DD House official social media and online presence: Official {platform} page is {url}. Note: Instagram is for updates and social media only; ordering through Instagram is not supported."
                chunks.append(DocumentChunk(
                    chunk_id=f"chunk_social_{rec_id}",
                    text=txt,
                    category="social",
                    source_type=source_type,
                    verified=verified,
                    policy="social_links",
                    last_updated=last_updated,
                    status=status
                ))

            elif cat in {"allergen", "ingredient"}:
                prod = r.get("product", "")
                txt = f"Allergen and ingredient information for {prod or 'products'} is currently UNKNOWN / TBD. Do not assume products are eggless or allergen-free."
                chunks.append(DocumentChunk(
                    chunk_id=f"chunk_tbd_{rec_id}",
                    text=txt,
                    category=cat,
                    source_type="unknown",
                    verified=False,
                    product=prod,
                    policy="tbd_ingredient_allergen",
                    last_updated=last_updated,
                    status="TBD"
                ))

        # Master Business Overview Chunk
        chunks.append(DocumentChunk(
            chunk_id="chunk_business_overview",
            text="DD House (DD HOUSE KKD) is a popular bakery and cake/food store in Kakinada, Andhra Pradesh. Store address: Venkat Nagar, Jayendra Nagar, Siddartha Nagar, Kakinada, Andhra Pradesh – 533003. Operating hours: DD House is open every day (Monday to Sunday) from 4:00 PM to 11:00 PM. Contact number: 7013522727. Official Instagram: https://www.instagram.com/ddhousekkd/. We specialize in fresh Cake Bowls, Brownies, and Cake Lollipops. Store pickup only (no home delivery).",
            category="business",
            source_type="business_provided",
            verified=True,
            policy="business_overview",
            last_updated="2026-09-18",
            status="active"
        ))

        # Master Product Catalogue Overview Chunk
        chunks.append(DocumentChunk(
            chunk_id="chunk_product_catalogue_overview",
            text="DD House sells delicious cake bowls, brownies, and cake lollipops. The complete DD House product catalogue and menu includes:\n1. Cake Bowls (₹89 to ₹99): Chocolate Cake Bowl (₹89), Double Chocolate (₹89), Triple Chocolate (₹99), Choco Truffle (₹99), Nutella (₹89), Oreo (₹89), Vanilla (₹89), Butterscotch (₹89).\n2. Brownies (₹50): Chocolate Brownie (₹50), Choco-Chip Brownie (₹50).\n3. Cake Lollipops (₹30): Chocolate Lollipop (₹30), Vanilla Lollipop (₹30).\nAll currently listed DD House products are available every day. The cheapest items on the menu are Cake Lollipops at ₹30.",
            category="product",
            source_type="business_provided",
            verified=True,
            policy="product_catalogue",
            last_updated="2026-09-18",
            status="active"
        ))

        # Overview chunks for menu categories
        chunks.append(DocumentChunk(
            chunk_id="chunk_menu_cake_bowls_summary",
            text="DD House cake bowls menu: Chocolate Cake Bowl (₹89), Double Chocolate (₹89), Triple Chocolate (₹99), Choco Truffle (₹99), Nutella (₹89), Oreo (₹89), Vanilla (₹89), and Butterscotch (₹89). All 8 cake bowl varieties cost ₹89 or ₹99 and are available every day.",
            category="product",
            source_type="business_provided",
            verified=True,
            product_category="cake_bowl",
            policy="menu_cake_bowls",
            last_updated="2026-09-18",
            status="active"
        ))
        chunks.append(DocumentChunk(
            chunk_id="chunk_menu_brownies_summary",
            text="DD House brownie menu: Chocolate Brownie costs ₹50 and Choco-Chip Brownie costs ₹50. Both brownies are available daily and cannot be customized.",
            category="product",
            source_type="business_provided",
            verified=True,
            product="Brownie",
            product_category="brownie",
            policy="menu_brownies",
            last_updated="2026-09-18",
            status="active"
        ))
        chunks.append(DocumentChunk(
            chunk_id="chunk_menu_lollipops_summary",
            text="DD House cake lollipops menu: Chocolate Lollipop (₹30) and Vanilla Lollipop (₹30). Both cake lollipops cost ₹30, are the cheapest items on the menu, and are available daily.",
            category="product",
            source_type="business_provided",
            verified=True,
            product_category="cake_lollipop",
            policy="menu_lollipops",
            last_updated="2026-09-18",
            status="active"
        ))

        return chunks

