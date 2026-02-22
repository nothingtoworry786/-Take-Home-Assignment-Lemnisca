import os
from pathlib import Path

# Load .env from project root (parent of backend/) if python-dotenv is installed
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass  # GROQ_API_KEY etc. must be set in the environment


class Config:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    Groq_url: str = os.getenv("GROQ_URL")
    SMALL_MODEL: str = "llama-3.1-8b-instant"
    BIG_MODEL: str = "llama-3.3-70b-versatile"
    TOP_K: int = 10
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100
    PORT: int = int(os.getenv("PORT", "8000"))