from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "LLMAPI Client Gateway"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/client/v1"

    LLMAPI_BASE_URL: str = "http://localhost:8001/v1"
    LLMAPI_TIMEOUT_SECONDS: float = 30.0
    DEFAULT_PROMPT_VERSION: str = "v1.1"

    MYSQL_DSN: str = "mysql+pymysql://root:password@localhost:3306/client_gateway"
    REDIS_URL: str = "redis://localhost:6379/1"
    QUEUE_ENABLED: bool = False

    AUTH_SHARED_KEY: str = ""
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
