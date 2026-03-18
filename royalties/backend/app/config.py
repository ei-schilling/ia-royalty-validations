"""Application configuration loaded from environment variables."""


from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings driven by environment variables."""

    database_url: str = "postgresql+asyncpg://validator:validator@localhost:5432/validator"
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    allowed_extensions: str = "csv,xlsx,json,pdf"
    cors_origins: List[str] = ["http://localhost:5173"]
    log_level: str = "INFO"
    amount_tolerance: float = 0.01
    max_rate_threshold: float = 1.00

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


settings = Settings()
