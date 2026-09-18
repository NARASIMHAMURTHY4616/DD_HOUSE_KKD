import json
import logging
from pathlib import Path
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.database.connection import connect_to_mongo, ensure_indexes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def seed_products():
    seed_file = Path(__file__).resolve().parent / "products.json"
    if not seed_file.exists():
        logger.error(f"Seed file not found at {seed_file}")
        sys.exit(1)

    with open(seed_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    db = connect_to_mongo()
    if db is None:
        logger.error("Could not obtain MongoDB database instance.")
        sys.exit(1)

    try:
        db.command("ping")
    except Exception as e:
        logger.error(f"Cannot reach MongoDB server at {db.client.HOST if hasattr(db, 'client') else 'localhost'}: {e}")
        logger.info("Ensure your MongoDB server is started (or MONGODB_URI is set in .env).")
        sys.exit(1)

    ensure_indexes(db)

    inserted_or_updated = 0
    for product in products:
        product_id = product.get("product_id")
        if not product_id:
            continue
        db.products.update_one(
            {"product_id": product_id},
            {"$set": product},
            upsert=True
        )
        inserted_or_updated += 1

    logger.info(f"Successfully seeded/upserted {inserted_or_updated} verified products into 'products' collection.")


if __name__ == "__main__":
    seed_products()
