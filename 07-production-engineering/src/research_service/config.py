"""Environment configuration, validated once at application startup."""

from typing import Literal

from pydantic import Field, SecretStr, model_validator
from research_sdk.config import Settings as SDKSettings


class Settings(SDKSettings):
    database_url: str = "sqlite:///./researchops.db"
    environment: Literal["local", "production"] = "local"
    demo_mode: bool = False
    # JSON mapping SHA-256 bearer-token digests to server-owned identities.
    api_principals: SecretStr = SecretStr("{}")
    max_request_bytes: int = Field(default=131072, ge=1024, le=1048576)
    max_concurrent_requests: int = Field(default=16, ge=1, le=256)
    requests_per_minute: int = Field(default=120, ge=1, le=10000)
    max_pending_runs: int = Field(default=100, ge=1, le=10000)
    auto_migrate: bool = True

    @model_validator(mode="after")
    def production_configuration(self):
        if self.environment == "production":
            if self.demo_mode or self.api_principals.get_secret_value().strip() in ("", "{}"):
                raise ValueError(
                    "Production requires configured identities and demo mode disabled."
                )
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires PostgreSQL with the psycopg driver.")
            if self.auto_migrate:
                raise ValueError(
                    "Run migrations separately and disable AUTO_MIGRATE in production."
                )
        return self
