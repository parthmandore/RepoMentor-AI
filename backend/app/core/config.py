import os
import tempfile
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"), env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    PROJECT_NAME: str = "Repository Mentor AI"
    API_V1_STR: str = "/api/v1"
    
    # Required Database Configuration (Component 8 & 9)
    DATABASE_URL: str
    
    # Supabase credentials (Optional backend metadata)
    SUPABASE_URL: Optional[str] = ""
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = ""
    SUPABASE_ANON_KEY: Optional[str] = ""

    # Groq LLM Configuration (Component 3 & 9)
    GROQ_API_KEY: str
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")
    GROQ_RPM_LIMIT: int = 30
    GROQ_TPM_LIMIT: int = 8000

    # External Embedding API Configuration (Render Free Zero-ML Architecture)
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "gemini")
    EMBEDDING_API_KEY: Optional[str] = os.getenv("EMBEDDING_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))

    # Phase A Analysis Budget (Seconds) - Default 90s for Render Free
    ANALYSIS_BUDGET_SECONDS: int = 90

    # Worker processes / threads concurrency setting (Render Free plan = 1)
    WORKERS: int = 1

    # Storage settings for ephemeral clones (strictly in /tmp on Render / Linux)
    CLONE_DIR: str = os.getenv("CLONE_DIR", os.path.join(tempfile.gettempdir(), "repomentor_clones"))

    # Flag to conditionally enable/disable Knowledge Base (embeddings generation) to save memory/credits
    ENABLE_KNOWLEDGE_BASE: bool = True

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
        "https://repomentor.netlify.app"
    ]

    # Timeout & Retry Settings
    GIT_CLONE_TIMEOUT: int = 120
    GIT_CLONE_RETRIES: int = 3
    GROQ_TIMEOUT: float = 60.0
    GROQ_RETRIES: int = 3
    KNOWLEDGE_TIMEOUT_SECONDS: int = 300
    ASSESSMENT_TIMEOUT_SECONDS: int = 120

settings = Settings()
