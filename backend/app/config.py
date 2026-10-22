from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://insights:insights@localhost:5432/insights"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model_fast: str = "gemma-4-26b-a4b"
    llm_model_smart: str = "glm-5.3-flash"
    llm_daily_token_limit: int = 2_000_000
    llm_timeout_sec: float = 90.0

    companies_csv: str = "/app/data/df_Uid_data_hack.csv"
    persons_csv: str = "/app/data/df_Fid_Uid_link_hack.csv"
    payments_csv: str = "/app/data/payments.csv"
    sample_companies_csv: str = "/app/data/sample_companies.csv"
    alfa_analytics_dir: str = "/app/data/alfa_analytics"

    news_ingest_interval_min: int = 30
    # Порог «крупного бизнеса» из кейса — выручка свыше 15 млрд ₽
    large_business_revenue: float = 15_000_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
