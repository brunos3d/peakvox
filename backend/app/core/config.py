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
    # Local scratch space for inference I/O (objects are downloaded here before
    # being fed to the model, and results are written here before upload).
    TMP_DIR: Path = Path("/data/tmp")

    # MinIO / S3-compatible object storage — source of truth for all audio.
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "omnivoice"
    MINIO_SECURE: bool = False

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://frontend:3000"]

    def create_dirs(self) -> None:
        for d in [self.VOICES_DIR, self.UPLOADS_DIR, self.GENERATED_DIR, self.TMP_DIR]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
