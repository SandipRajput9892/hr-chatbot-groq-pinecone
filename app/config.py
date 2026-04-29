from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Application
    APP_NAME: str = "HR Chatbot"
    APP_ENV: str = "development"
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Database
    DATABASE_URL: str

    # Initial admin (created on first startup if no admin exists)
    INITIAL_ADMIN_EMAIL: Optional[str] = None
    INITIAL_ADMIN_PASSWORD: Optional[str] = None
    INITIAL_ADMIN_NAME: str = "System Admin"
    INITIAL_ADMIN_EMPLOYEE_ID: str = "ADMIN001"

    # Groq
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "hr-chatbot"
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_CLOUD: str = "aws"

    # Embeddings (local sentence-transformers model)
    EMBEDDING_MODEL: str = "llama-text-embed-v2"
    EMBEDDING_DIMENSION: int = 1024

    # File upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10 MB
    UPLOAD_DIR: str = "uploads"

    # Zoho HR webhook
    ZOHO_WEBHOOK_TOKEN: Optional[str] = None


settings = Settings()
