import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # App
    APP_NAME: str = "StudyMentor AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, validation_alias="DEBUG")
    ENVIRONMENT: str = Field(default="development", validation_alias="ENVIRONMENT")
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = Field(validation_alias="DATABASE_URL")
    
    # JWT Auth
    SECRET_KEY: str = Field(validation_alias="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # OpenAI (optional - for GPT models)
    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7

    # Groq (recommended - fast, free tier available)
    # Get from https://console.groq.com/keys
    GROQ_API_KEY: str = Field(default="", validation_alias="GROQ_API_KEY")
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_MAX_TOKENS: int = 8192
    GROQ_TEMPERATURE: float = 0.7

    @field_validator("GROQ_API_KEY")
    @classmethod
    def validate_groq_key(cls, v: str) -> str:
        if v and not v.startswith("gsk_"):
            raise ValueError("GROQ_API_KEY must start with 'gsk_'")
        return v
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5500"]
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()