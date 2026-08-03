from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "SMART CASH & CARRY"
    DEBUG: bool = True
    SECRET_KEY: str = "development-only-change-me"
    DATABASE_URL: str = "sqlite:///./ai_fatah.db"
    AUTO_CREATE_TABLES: bool = True
    WHATSAPP_NUMBER: str = "923001234567"
    ADMIN_EMAIL: str = "admin@aifatah.pk"
    ADMIN_PASSWORD: str = "ChangeMe123!"
    SESSION_HTTPS_ONLY: bool = False
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/webp"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def upload_dir(self) -> Path:
        return BASE_DIR / "uploads"

    @property
    def templates_dir(self) -> Path:
        return BASE_DIR / "app" / "templates"

    @property
    def static_dir(self) -> Path:
        return BASE_DIR / "app" / "static"

    @property
    def allowed_image_types(self) -> set[str]:
        return {value.strip() for value in self.ALLOWED_IMAGE_TYPES.split(",") if value.strip()}


settings = Settings()

# ✅ Branches data (just below settings)
BRANCHES = [
    {"id": "zafarwal", "name": "Zafarwal", "whatsapp": "923270880226"},
    {"id": "narowal", "name": "Narowal", "whatsapp": "923327777263"},
    {"id": "shakrghar", "name": "Shakrghar", "whatsapp": "923456666238"},
    {"id": "kingra", "name": "Kingra", "whatsapp": "923003333333"},
    {"id": "pusrur", "name": "Pusrur", "whatsapp": "923004444444"},
]