from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
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
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Local FastEmbed Configuration
    EMBEDDING_DIMENSION: int = 384  # Dimension of BAAI/bge-small-en-v1.5

    # Storage settings for preserved clones
    CLONE_DIR: str = "temp_clones"

    # Flag to conditionally enable/disable Knowledge Base (embeddings generation) to save memory/credits
    ENABLE_KNOWLEDGE_BASE: bool = True

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
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
