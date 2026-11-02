from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-6-astra"
    request_timeout_seconds: float = Field(default=30, gt=0, le=120)
    openai_max_retries: int = Field(default=2, ge=0, le=3)
    max_output_tokens: int = Field(default=1024, ge=16, le=4096)

    @property
    def configured(self):
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value().strip())
