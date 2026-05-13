from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Chat Backend"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    MONGO_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "ai_chat_app"

    JWT_SECRET_KEY: str = Field(default="super_secret_key")
    JWT_REFRESH_SECRET: str = Field(default="super_refresh_secret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OTP_EXPIRE_MINUTES: int = 10
    OTP_LENGTH: int = 6
    RETURN_OTP_IN_RESPONSE: bool = True
    TWO_FACTOR_API_KEY: str = ""
    TWO_FACTOR_SMS_TIMEOUT_SECONDS: int = 10
    GOOGLE_CLIENT_ID: str = ""
    
    # SMTP Settings for Email OTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # LLM API Keys
    MISTRAL_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "mistral-large-latest"

    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
