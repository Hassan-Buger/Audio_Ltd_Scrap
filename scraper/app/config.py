"""Application configuration using Pydantic Settings."""
from typing import List, Union, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    # Operator API key. Development fallback only; production MUST set API_KEY
    # via the Railway environment variable. Never commit a real key here.
    API_KEY: Optional[str] = Field(
        default="dev-operator-api-key-change-in-production",
        description="Operator API key (dev fallback; production must set via env).",
    )
    SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Application secret key. Required in production; set via env.",
    )
    # Explicit allowlist for CORS. Production should list the Railway host(s).
    # Local development includes http://localhost:8000.
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "https://audioltdscrap-production.up.railway.app",
        "https://audioltdscrap-production-540ccae2.up.railway.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ]

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./audiovideo.db",
        description="SQLAlchemy database URL. Defaults to local SQLite if Postgres is unavailable."
    )

    # Task Broker / Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Scraper limits & policies
    TARGET_ALLOWED_HOSTS: Union[str, List[str]] = ["www.audiovideo.lt", "audiovideo.lt"]
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    SCRAPER_COOKIES: Optional[str] = Field(
        default=None,
        description="Optional session or cf_clearance cookies obtained from an authorized human browser session."
    )
    # Residential proxy or FlareSolverr endpoint to bypass datacenter IP blocks
    RESIDENTIAL_PROXY_URL: Optional[str] = Field(
        default=None,
        description="Residential proxy URL (e.g. http://user:pass@gate.smartproxy.com:7000) for crawling and image downloads."
    )
    FLARESOLVERR_URL: Optional[str] = Field(
        default=None,
        description="Optional FlareSolverr instance URL (e.g. http://localhost:8191/v1) for challenge resolution."
    )
    # Public service base URL used to rewrite image and API links
    BASE_URL: str = Field(
        default="https://audioltdscrap-production-540ccae2.up.railway.app",
        description="Public base URL of this application service."
    )
    MEDIA_DIR: str = Field(
        default="data/media",
        description="Local directory for caching and serving downloaded product images."
    )
    CRAWL_CONCURRENCY: int = 2
    CRAWL_DOWNLOAD_DELAY: float = 2.0
    CRAWL_MAX_RETRIES: int = 3
    CRAWL_MAX_DEPTH: int = 10
    CRAWL_MAX_URLS_PER_JOB: int = 50000
    USE_PLAYWRIGHT_FALLBACK: bool = False

    # Translation
    TRANSLATION_ENABLED: bool = False
    TRANSLATION_PROVIDER: str = "none"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Optional[str]) -> str:
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v or "sqlite:///./audiovideo.db"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("TARGET_ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_target_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        """Fail fast in production if required secrets are missing or still dev fallbacks."""
        if self.ENV == "production":
            if (
                not self.API_KEY
                or self.API_KEY == "dev-operator-api-key-change-in-production"
            ):
                raise ValueError(
                    "API_KEY must be set via the Railway environment variable in production; "
                    "the dev fallback is not allowed."
                )
            if not self.SECRET_KEY:
                raise ValueError(
                    "SECRET_KEY must be set via the Railway environment variable in production."
                )
        return self


settings = Settings()
