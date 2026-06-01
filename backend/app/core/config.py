from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "OmniVoice Platform"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:////data/omnivoice.db"

    OMNIVOICE_MODEL: str = "k2-fsa/OmniVoice"
    LOAD_ASR: bool = False
    ASR_MODEL: str = "openai/whisper-large-v3-turbo"
    HF_HOME: str = "/data/models"

    DATA_DIR: Path = Path("/data")
    VOICES_DIR: Path = Path("/data/voices")
    UPLOADS_DIR: Path = Path("/data/uploads")
    GENERATED_DIR: Path = Path("/data/generated")

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://frontend:3000"]

    def create_dirs(self) -> None:
        for d in [self.VOICES_DIR, self.UPLOADS_DIR, self.GENERATED_DIR]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
