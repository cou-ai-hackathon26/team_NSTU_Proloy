import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
_backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_backend_env, _root_env, ".env"),
        extra="allow"
    )

    APP_NAME: str = "Shoi (সই) - Health Assistant"
    DEBUG: bool = True
    SECRET_KEY: str = "shoi-secret-key-change-in-production-random-uuid-64738291"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 90

    # Database - Absolute path to root shoi.db to avoid cwd discrepancies
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shoi.db'))}"
    )

    # LLM Settings - Open-source, Local & Multi-provider
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # gemini, ollama, openai_compatible, or mock
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Voice / Audio Settings
    TTS_ENGINE: str = "edge-tts"  # edge-tts, gtts, or web
    BANGLA_VOICE: str = "bn-BD-NabanitaNeural"  # Natural Bangla voice
    WHISPER_MODEL: str = "base"

    # RAG Settings
    KB_CONFIDENCE_THRESHOLD: float = 0.45

settings = Settings()
