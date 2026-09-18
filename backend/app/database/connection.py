import logging
from typing import Optional
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database
from backend.app.config.settings import settings

logger = logging.getLogger(__name__)


class MongoDBConnection:
    client: Optional[MongoClient] = None
    db: Optional[Database] = None


mongo_conn = MongoDBConnection()


def get_database() -> Database:
    """Return the active database instance."""
    if mongo_conn.db is None:
        # If not connected yet (e.g. during script runs or lazy initialization), initialize
        connect_to_mongo()
    return mongo_conn.db


def connect_to_mongo(uri: Optional[str] = None, db_name: Optional[str] = None) -> Database:
    """Establish connection to MongoDB and ensure indexes."""
    target_uri = uri or settings.MONGODB_URI
    target_db_name = db_name or settings.DATABASE_NAME
    try:
        mongo_conn.client = MongoClient(
            target_uri,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000
        )
        mongo_conn.db = mongo_conn.client[target_db_name]
        logger.info(f"Connected to MongoDB at {target_uri}, database: {target_db_name}")
        ensure_indexes(mongo_conn.db)
        return mongo_conn.db
    except Exception as e:
        logger.warning(f"Could not connect to live MongoDB: {e}")
        # When live MongoDB is not running locally during development, db remains set if client created
        if mongo_conn.client is not None:
            mongo_conn.db = mongo_conn.client[target_db_name]
        return mongo_conn.db


def close_mongo_connection():
    """Close MongoDB connection gracefully."""
    if mongo_conn.client:
        mongo_conn.client.close()
        mongo_conn.client = None
        mongo_conn.db = None
        logger.info("MongoDB connection closed.")


def set_test_database(mock_db: Database):
    """Explicitly inject a mock database for tests."""
    mongo_conn.db = mock_db
    ensure_indexes(mock_db)


def ensure_indexes(db: Optional[Database] = None):
    """Ensure unique and query indexes on products and orders collections."""
    target_db = db if db is not None else mongo_conn.db
    if target_db is None:
        return
    try:
        # Product indexes
        target_db.products.create_index([("product_id", ASCENDING)], unique=True)
        target_db.products.create_index([("category", ASCENDING)])
        target_db.products.create_index([("available", ASCENDING)])

        # Order indexes
        target_db.orders.create_index([("order_id", ASCENDING)], unique=True)
        target_db.orders.create_index([("customer.phone", ASCENDING)])
        target_db.orders.create_index([("status", ASCENDING)])
        target_db.orders.create_index([("created_at", ASCENDING)])

        logger.info("Database indexes ensured successfully.")
    except Exception as e:
        logger.warning(f"Could not ensure indexes: {e}")
