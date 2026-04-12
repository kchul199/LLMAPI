from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "LLMAPI"
    APP_VERSION: str = "1.2.0"
    API_V1_STR: str = "/v1"
    
    # Main LLM Settings
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "llama3.2:3b"
    
    # Backup LLM Settings (for Fail-over)
    LLM_BACKUP_BASE_URL: str = "http://localhost:11434/v1"
    LLM_BACKUP_API_KEY: Optional[str] = None
    LLM_BACKUP_MODEL_NAME: Optional[str] = "llama3.2:1b"

    # LLM Retry/Circuit Breaker
    LLM_RETRY_ATTEMPTS: int = 2
    LLM_RETRY_MIN_WAIT_SECONDS: int = 1
    LLM_RETRY_MAX_WAIT_SECONDS: int = 4
    LLM_CB_FAILURE_THRESHOLD: int = 3
    LLM_CB_RECOVERY_SECONDS: int = 30
    LLM_CB_HALF_OPEN_MAX_CALLS: int = 1

    # LLM Timeout Policy (per task)
    LLM_TIMEOUT_MIN_SECONDS: float = 10.0
    LLM_TIMEOUT_SUMMARY_SECONDS: float = 45.0
    LLM_TIMEOUT_SENTIMENT_SECONDS: float = 25.0
    LLM_TIMEOUT_CATEGORY_SECONDS: float = 25.0
    LLM_TIMEOUT_MULTI_TASK_OVERHEAD_SECONDS: float = 8.0
    LLM_TIMEOUT_BACKUP_MULTIPLIER: float = 0.8

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_QUEUE_ENABLED: bool = False
    REDIS_QUEUE_KEY: str = "llmapi:analysis:queue"
    REDIS_JOB_KEY_PREFIX: str = "llmapi:analysis:job"
    REDIS_JOB_TTL_SECONDS: int = 600
    REDIS_QUEUE_WORKER_CONCURRENCY: int = 1
    
    # Operational Settings
    LOG_LEVEL: str = "INFO"
    PROMPT_CONFIG_FILE: str = "src/core/prompts.yaml"
    
    # Security
    SECRET_KEY: str = "dev_secret_key"
    ALLOWED_HOSTS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
