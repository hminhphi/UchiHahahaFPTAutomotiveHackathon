"""Strict environment-backed API configuration."""

from collections.abc import Mapping
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiSettings(BaseModel):
    """Validated settings for one API process."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    testing: bool = False
    allowed_origins: tuple[str, ...] = ("http://localhost:3000",)
    redis_url: str | None = None
    database_url: str | None = None
    replay_enabled: bool = False
    replay_fps: float = Field(default=10.0, gt=0, le=30)
    replay_loop: bool = True
    media_backend: Literal["filesystem", "s3"] = "filesystem"
    dataset_root: Path = Path("data/Practice_Dataset/Practice_Dataset")
    object_storage_endpoint: str | None = None
    object_storage_bucket: str = "fleetiq-demo"
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None
    max_metadata_bytes: int = Field(default=64 * 1024, ge=128, le=1024 * 1024)
    max_frame_bytes: int = Field(default=8 * 1024 * 1024, ge=4, le=64 * 1024 * 1024)

    @model_validator(mode="after")
    def validate_runtime(self) -> Self:
        if not self.allowed_origins:
            raise ValueError("at least one explicit CORS origin is required")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("CORS origins must be explicit HTTP(S) origins")
            if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError("CORS origins cannot contain a path, query, or fragment")
        if not self.testing and (not self.redis_url or not self.database_url):
            raise ValueError(
                "production configuration requires Redis and database URLs; "
                "for local fixture mode set FLEETIQ_TESTING=true, or provide "
                "FLEETIQ_REDIS_URL and FLEETIQ_DATABASE_URL"
            )
        if self.redis_url is not None:
            redis = urlsplit(self.redis_url)
            if redis.scheme not in {"redis", "rediss"} or not redis.hostname:
                raise ValueError("Redis URL must use redis:// or rediss:// with a host")
        if self.database_url is not None:
            database = urlsplit(self.database_url)
            if database.scheme not in {"postgres", "postgresql"} or not database.hostname:
                raise ValueError("database URL must use postgres:// or postgresql:// with a host")
        if self.media_backend == "s3":
            if not self.object_storage_endpoint:
                raise ValueError("S3 media backend requires FLEETIQ_OBJECT_STORAGE_ENDPOINT")
            if not self.object_storage_access_key or not self.object_storage_secret_key:
                raise ValueError("S3 media backend requires object storage credentials")
            endpoint = urlsplit(self.object_storage_endpoint)
            if endpoint.scheme not in {"http", "https"} or not endpoint.netloc:
                raise ValueError("object storage endpoint must be an HTTP(S) URL")
        return self

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str],
        *,
        testing_override: bool | None = None,
    ) -> Self:
        """Parse only the supported environment variables with strict conversions."""

        def parse_bool(name: str, default: bool) -> bool:
            raw = environment.get(name)
            if raw is None:
                return default
            normalized = raw.strip().casefold()
            if normalized in {"1", "true", "yes"}:
                return True
            if normalized in {"0", "false", "no"}:
                return False
            raise ValueError(f"{name} must be true or false")

        def parse_int(name: str, default: int) -> int:
            raw = environment.get(name)
            if raw is None:
                return default
            try:
                return int(raw)
            except ValueError as error:
                raise ValueError(f"{name} must be an integer") from error

        testing = testing_override if testing_override is not None else parse_bool("FLEETIQ_TESTING", False)
        origins_raw = environment.get("FLEETIQ_ALLOWED_ORIGINS", "http://localhost:3000")
        origins = tuple(item.strip() for item in origins_raw.split(",") if item.strip())
        return cls(
            testing=testing,
            allowed_origins=origins,
            redis_url=environment.get("FLEETIQ_REDIS_URL"),
            database_url=environment.get("FLEETIQ_DATABASE_URL"),
            replay_enabled=parse_bool("FLEETIQ_REPLAY_ENABLED", False),
            replay_fps=float(environment.get("FLEETIQ_REPLAY_FPS", "10")),
            replay_loop=parse_bool("FLEETIQ_REPLAY_LOOP", True),
            media_backend=environment.get("FLEETIQ_MEDIA_BACKEND", "filesystem"),
            dataset_root=Path(
                environment.get(
                    "FLEETIQ_DATASET_ROOT", "data/Practice_Dataset/Practice_Dataset"
                )
            ),
            object_storage_endpoint=environment.get("FLEETIQ_OBJECT_STORAGE_ENDPOINT"),
            object_storage_bucket=environment.get("FLEETIQ_OBJECT_STORAGE_BUCKET", "fleetiq-demo"),
            object_storage_access_key=environment.get("FLEETIQ_OBJECT_STORAGE_ACCESS_KEY"),
            object_storage_secret_key=environment.get("FLEETIQ_OBJECT_STORAGE_SECRET_KEY"),
            max_metadata_bytes=parse_int("FLEETIQ_MAX_METADATA_BYTES", 64 * 1024),
            max_frame_bytes=parse_int("FLEETIQ_MAX_FRAME_BYTES", 8 * 1024 * 1024),
        )
