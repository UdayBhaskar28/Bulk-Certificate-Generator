import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

# Detect serverless environment (Vercel, AWS Lambda)
IS_SERVERLESS = bool(
    os.getenv("VERCEL")
    or os.getenv("VERCEL_ENV")
    or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
    or os.getenv("LAMBDA_TASK_ROOT")
)

def get_default_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    if IS_SERVERLESS:
        return "sqlite:////tmp/bulk_certs.db"
    return f"sqlite:///{BASE_DIR / 'bulk_certs.db'}"

def get_default_storage_dir() -> Path:
    env_storage = os.getenv("STORAGE_DIR")
    if env_storage:
        return Path(env_storage)
    if IS_SERVERLESS:
        return Path("/tmp/storage/certificates")
    return BASE_DIR / "storage" / "certificates"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Bulk Certificate Generator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    IS_SERVERLESS: bool = IS_SERVERLESS
    
    # Database
    DATABASE_URL: str = get_default_database_url()
    
    # Storage
    STORAGE_DIR: Path = get_default_storage_dir()
    
    # Processing
    MAX_RECIPIENTS_PER_BATCH: int = 1000

settings = Settings()

# Ensure storage directory exists (fail-safe for read-only filesystem)
try:
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
