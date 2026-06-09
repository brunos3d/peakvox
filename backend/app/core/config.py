from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.features import Features


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "PeakVox"
    DEBUG: bool = False

    # Deployment edition. "community" (default) is fully self-hosted and
    # authentication-free. "cloud" / "enterprise" are reserved for future editions and
    # only change which identity/billing/tenancy extensions are wired in — never the
    # core schema. See docs/SAAS_ARCHITECTURE.md.
    EDITION: str = "community"

    # Single implicit local owner for the self-hosted Community Edition. The schema is
    # SaaS-ready (every resource carries owner_id), but no authentication exists yet —
    # all resources belong to this seeded system user. Real auth can later add user
    # rows + a current_user dependency without a schema redesign.
    LOCAL_OWNER_ID: str = "00000000-0000-0000-0000-000000000001"
    LOCAL_OWNER_HANDLE: str = "local"
    LOCAL_OWNER_DISPLAY_NAME: str = "Local User"

    DATABASE_URL: str = "sqlite+aiosqlite:////data/omnivoice.db"

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

    # Voice variant artifact retention (ADR-0009). CE keeps the active artifact plus the last
    # N versions so recent rebuilds remain rollback-able without unbounded storage growth.
    # Cloud overrides this with marketplace-grade retention.
    ARTIFACT_RETENTION_COUNT: int = 3

    # Fish Audio S2 Pro remote server URL. The server runs separately (api_server.py or
    # SGLang Omni) and the adapter connects via HTTP. Set to empty string to keep the
    # model disabled when no Fish backend is available.
    FISH_AUDIO_SERVER_URL: str = "http://localhost:8080"

    # Path to the runtime-registry/ directory. The default points
    # to the in-repo runtime-registry/ directory. The CE
    # descriptor for Kokoro lives at
    # <path>/kokoro-82m/descriptor.json. Deployments can override
    # the path via env var (RUNTIME_REGISTRY_PATH) to a different
    # mount or to a custom location.
    RUNTIME_REGISTRY_PATH: Path = Path(__file__).resolve().parent.parent.parent.parent / "runtime-registry"

    # Runtime subsystem wiring (R3). When True (the CE default since Task 21),
    # startup constructs RuntimeRegistryLoader, DockerRuntimeDriver, RuntimeManager,
    # attaches the manager to PeakVoxRuntime, and starts the idle reaper. Runtime
    # containers are never started automatically — the user installs and activates
    # models via the Models page (R6 — lazy activation).
    RUNTIME_SERVICE_ENABLED: bool = True

    @property
    def features(self) -> Features:
        return Features.for_edition(self.EDITION)

    def create_dirs(self) -> None:
        for d in [self.VOICES_DIR, self.UPLOADS_DIR, self.GENERATED_DIR, self.TMP_DIR]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
