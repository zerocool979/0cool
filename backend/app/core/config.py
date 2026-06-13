from pydantic_settings import BaseSettings
from typing import List, Literal


class Settings(BaseSettings):
    APP_NAME: str = "NmapSLM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # AI Provider
    DEFAULT_AI_PROVIDER: Literal["gemini", "slm"] = "gemini"

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT: int = 120

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "xploiter/pentester:v2"
    OLLAMA_TIMEOUT: int = 120

    # Nmap
    NMAP_TIMEOUT: int = 300  # 5 minutes max scan
    MAX_CONCURRENT_SCANS: int = 3

    # Reports
    REPORTS_DIR: str = "/tmp/nmap_slm_reports"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
