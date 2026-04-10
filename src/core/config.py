from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "LLMAPI"
    API_V1_STR: str = "/v1"
    
    # Main LLM Settings
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "llama3.2:3b"
    
    # Backup LLM Settings (for Fail-over)
    LLM_BACKUP_BASE_URL: str = "http://localhost:11434/v1"
    LLM_BACKUP_MODEL_NAME: str = "llama3.2:1b"
    
    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
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
