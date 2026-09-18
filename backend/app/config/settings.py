from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000

    # MongoDB settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "dd_house_kakinada"

    # CORS settings
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Store Information
    STORE_PHONE: str = "7013522727"
    STORE_NAME: str = "DD House"
    STORE_LOCATION: str = "Venkat Nagar, Jayendra Nagar, Siddartha Nagar, Kakinada, Andhra Pradesh – 533003"
    STORE_OPENING_TIME: str = "16:00"
    STORE_CLOSING_TIME: str = "23:00"

    # RAG Integration URL
    RAG_SERVICE_URL: str = "http://localhost:8001"

    # Payment workflow configuration (TBD for cash advance timing)
    CASH_PAYMENT_DEFAULT_STATUS: str = "PENDING"
    CASH_ORDER_DEFAULT_STATUS: str = "PENDING_PAYMENT"

    # Store authorization token for internal status management
    STORE_INTERNAL_TOKEN: str = "dd-store-secret-2026"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
