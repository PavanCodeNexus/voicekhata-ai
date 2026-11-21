import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "VoiceKhata AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "voicekhata-hackathon-secret-key-2026")
    
    # Database
    DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "voice_khata.db"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://chymnlwzaztecurdhoaj.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "sb_publishable_xbaO8_-rAHU6ew6rxP6Dsw_lSBVy5fp")
    
    # Gnani API Platform
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
    GNANI_TOKEN: str = os.getenv("GNANI_TOKEN", "")
    GNANI_STT_WS_URL: str = os.getenv("GNANI_STT_WS_URL", "wss://api.gnani.ai/v1/prisma/stream")
    GNANI_TTS_WS_URL: str = os.getenv("GNANI_TTS_WS_URL", "wss://api.gnani.ai/v1/timbre/stream")
    
    # Optional LLM Fallback (Groq)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    
    # Shop Info
    SHOP_NAME: str = os.getenv("SHOP_NAME", "Sri Krishna Provision Stores")
    SHOP_TIMEZONE: str = os.getenv("SHOP_TIMEZONE", "Asia/Kolkata")
    SHOP_DEFAULT_LANG: str = os.getenv("SHOP_DEFAULT_LANG", "kn-IN")
    SHOP_UPI_VPA: str = os.getenv("SHOP_UPI_VPA", "kirana@upi")
    
    # Storage dirs
    BILLS_DIR: Path = BASE_DIR / "bills_generated"
    EXPORTS_DIR: Path = BASE_DIR / "exports_generated"

settings = Settings()
settings.BILLS_DIR.mkdir(parents=True, exist_ok=True)
settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
