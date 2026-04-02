from pathlib import Path

from pydantic_settings import BaseSettings

# Look for .env in project root (parent of backend/); skip if not found (Docker uses env_file)
_env_file = Path(__file__).resolve().parents[2] / ".env"
if not _env_file.exists():
    _env_file = None


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://monitor:monitor_dev@localhost:5432/forbidden_word_monitor"

    # CLS
    tencent_secret_id: str = ""
    tencent_secret_key: str = ""
    cls_region: str = "ap-hongkong"
    cls_topic_id: str = "b772faa9-3ca0-42a1-9a85-b64dd2826ea0"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = {"env_file": str(_env_file) if _env_file else None, "extra": "ignore"}


settings = Settings()
