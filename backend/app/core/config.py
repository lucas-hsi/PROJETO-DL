from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "projetodl"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@postgres:5432/projetodl"
    )
    REDIS_URL: str = "redis://redis:6379/0"

    MERCADOLIVRE_SEED_LIMIT: int = 10
    ML_IMPORT_LIMIT: int = 100
    ML_RATE_LIMIT: int = 250
    ML_IMPORT_BATCH: int = 100
    ML_FULL_SYNC_BATCH: int = 300
    ML_FULL_SYNC_MAX: int | None = None

    # Shopify
    SHOPIFY_STORE_DOMAIN: str = ""
    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET_KEY: str = ""
    SHOPIFY_ACCESS_TOKEN: str = ""
    SHOPIFY_API_VERSION: str = ""
    SHOPIFY_API_BASE_URL: str = ""

    # Mercado Livre
    ML_CLIENT_ID: str = ""
    ML_CLIENT_SECRET: str = ""
    ML_REFRESH_TOKEN: str = ""
    ML_ACCESS_TOKEN: str = ""
    ML_SELLER_ID: str = ""
    ML_REDIRECT_URI: str = ""
    ML_API_BASE_URL: str = "https://api.mercadolibre.com"

    # JWT
    JWT_SECRET: str = "changeme-in-.env"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MIN: int = 480

    class Config:
        env_file = ".env"
        case_sensitive = False


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
