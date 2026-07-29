"""Injectable resource, repository, and live-stream interfaces."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from redis.exceptions import RedisError

from .schemas import AnalysisJob, AnalysisJobCreate, TripSummary
from .ws.frame_protocol import CameraFrame


class LifecycleResource(Protocol):
    async def start(self) -> None: ...

    async def close(self) -> None: ...

    async def ready(self) -> bool: ...


class TripRepository(Protocol):
    async def list_trips(self) -> tuple[TripSummary, ...]: ...


class JobRepository(Protocol):
    async def create(
        self,
        command: AnalysisJobCreate,
        *,
        idempotency_key: str,
    ) -> AnalysisJob: ...

    async def get(self, job_id: str) -> AnalysisJob | None: ...


class CameraFrameSink(Protocol):
    async def publish(self, trip_id: str, view: str, frame: CameraFrame) -> None: ...


class LatestStateSubscription(Protocol):
    queue: asyncio.Queue[dict[str, Any]]

    async def close(self) -> None: ...


class LatestStateBroker(Protocol):
    async def subscribe(self, trip_id: str) -> LatestStateSubscription: ...


class IdempotencyConflictError(ValueError):
    """Raised when one idempotency key is reused for a different command."""


class JobRepositoryUnavailableError(RuntimeError):
    """Raised when the durable job store cannot complete a bounded operation."""


class AsyncRedisClient(Protocol):
    async def eval(self, script: str, numkeys: int, *values: str) -> Any: ...

    async def get(self, key: str) -> Any: ...

    async def ping(self) -> Any: ...

    async def aclose(self) -> None: ...


_CREATE_JOB_SCRIPT = """
local existing = redis.call("GET", KEYS[1])
if existing then
  local decoded = cjson.decode(existing)
  if decoded["fingerprint"] == ARGV[1] then
    return {"existing", existing}
  end
  return {"conflict", existing}
end
redis.call("SET", KEYS[1], ARGV[2])
redis.call("SET", KEYS[2], ARGV[3])
return {"created", ARGV[2]}
"""


class RedisJobRepository:
    """Durable job repository with atomic, cross-process idempotency."""

    def __init__(self, client: AsyncRedisClient, *, timeout_seconds: float = 2.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Redis timeout must be positive")
        self._client = client
        self._timeout_seconds = timeout_seconds
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def close(self) -> None:
        self._started = False
        await self._client.aclose()

    async def ready(self) -> bool:
        if not self._started:
            return False
        try:
            return bool(await asyncio.wait_for(self._client.ping(), self._timeout_seconds))
        except (TimeoutError, RedisError, OSError):
            return False

    async def create(
        self,
        command: AnalysisJobCreate,
        *,
        idempotency_key: str,
    ) -> AnalysisJob:
        fingerprint = hashlib.sha256(
            command.model_dump_json().encode("utf-8")
        ).hexdigest()
        job = AnalysisJob(
            job_id=str(uuid4()),
            trip_id=command.trip_id,
            status="queued",
            idempotency_key=idempotency_key,
            created_at=datetime.now(UTC),
        )
        idempotency_payload = json.dumps(
            {
                "fingerprint": fingerprint,
                "job": job.model_dump(mode="json"),
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        job_payload = job.model_dump_json()
        idempotency_digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        idempotency_redis_key = f"fleetiq:v1:jobs:idempotency:{idempotency_digest}"
        job_redis_key = f"fleetiq:v1:jobs:{job.job_id}"
        try:
            result = await asyncio.wait_for(
                self._client.eval(
                    _CREATE_JOB_SCRIPT,
                    2,
                    idempotency_redis_key,
                    job_redis_key,
                    fingerprint,
                    idempotency_payload,
                    job_payload,
                ),
                self._timeout_seconds,
            )
        except TimeoutError:
            raise JobRepositoryUnavailableError("Redis job operation timed out") from None
        except (RedisError, OSError):
            raise JobRepositoryUnavailableError("Redis job operation failed") from None

        try:
            status = _redis_text(result[0])
            stored = json.loads(_redis_text(result[1]))
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise JobRepositoryUnavailableError("Redis returned invalid job data") from None
        if status == "conflict":
            raise IdempotencyConflictError(idempotency_key)
        if status not in {"created", "existing"}:
            raise JobRepositoryUnavailableError("Redis returned an invalid job status")
        try:
            return AnalysisJob.model_validate_json(
                json.dumps(stored["job"], ensure_ascii=True, separators=(",", ":"))
            )
        except (KeyError, TypeError, ValueError):
            raise JobRepositoryUnavailableError("Redis returned invalid job data") from None

    async def get(self, job_id: str) -> AnalysisJob | None:
        try:
            value = await asyncio.wait_for(
                self._client.get(f"fleetiq:v1:jobs:{job_id}"),
                self._timeout_seconds,
            )
        except TimeoutError:
            raise JobRepositoryUnavailableError("Redis job lookup timed out") from None
        except (RedisError, OSError):
            raise JobRepositoryUnavailableError("Redis job lookup failed") from None
        if value is None:
            return None
        try:
            return AnalysisJob.model_validate_json(_redis_text(value))
        except (TypeError, ValueError):
            raise JobRepositoryUnavailableError("Redis returned invalid job data") from None


def _redis_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    raise TypeError("Redis response must be bytes or text")


@dataclass
class InMemoryHealthResource:
    _ready: bool = True
    started: bool = False
    closed: bool = False

    async def start(self) -> None:
        self.started = True
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    async def ready(self) -> bool:
        return self.started and not self.closed and self._ready

    def set_ready(self, value: bool) -> None:
        self._ready = value


@dataclass
class ConfiguredExternalResource:
    """Honest placeholder until a concrete Redis/PostgreSQL adapter is injected."""

    name: str
    url: str
    started: bool = False

    async def start(self) -> None:
        self.started = True

    async def close(self) -> None:
        self.started = False

    async def ready(self) -> bool:
        return False


@dataclass
class InMemoryTripRepository:
    trips: tuple[TripSummary, ...] = ()

    async def list_trips(self) -> tuple[TripSummary, ...]:
        return self.trips


@dataclass
class InMemoryJobRepository:
    jobs_by_id: dict[str, AnalysisJob] = field(default_factory=dict)
    jobs_by_idempotency_key: dict[str, AnalysisJob] = field(default_factory=dict)

    async def create(
        self,
        command: AnalysisJobCreate,
        *,
        idempotency_key: str,
    ) -> AnalysisJob:
        existing = self.jobs_by_idempotency_key.get(idempotency_key)
        if existing is not None:
            if existing.trip_id != command.trip_id:
                raise IdempotencyConflictError(idempotency_key)
            return existing
        job = AnalysisJob(
            job_id=str(uuid4()),
            trip_id=command.trip_id,
            status="queued",
            idempotency_key=idempotency_key,
            created_at=datetime.now(UTC),
        )
        self.jobs_by_id[job.job_id] = job
        self.jobs_by_idempotency_key[idempotency_key] = job
        return job

    async def get(self, job_id: str) -> AnalysisJob | None:
        return self.jobs_by_id.get(job_id)


@dataclass
class InMemoryCameraFrameSink:
    latest: dict[tuple[str, str], CameraFrame] = field(default_factory=dict)

    async def publish(self, trip_id: str, view: str, frame: CameraFrame) -> None:
        self.latest[(trip_id, view)] = frame


class InMemoryLatestStateSubscription:
    def __init__(
        self,
        broker: InMemoryLatestStateBroker,
        trip_id: str,
        queue: asyncio.Queue[dict[str, Any]],
    ) -> None:
        self._broker = broker
        self._trip_id = trip_id
        self.queue = queue
        self.closed = False

    async def close(self) -> None:
        if not self.closed:
            self._broker.unsubscribe(self._trip_id, self.queue)
            self.closed = True


class InMemoryLatestStateBroker:
    """One-slot subscriber queues enforce latest-state semantics."""

    def __init__(self) -> None:
        self._latest: dict[str, dict[str, Any]] = {}
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    async def subscribe(self, trip_id: str) -> InMemoryLatestStateSubscription:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1)
        self._subscribers.setdefault(trip_id, set()).add(queue)
        if trip_id in self._latest:
            queue.put_nowait(dict(self._latest[trip_id]))
        return InMemoryLatestStateSubscription(self, trip_id, queue)

    def publish_nowait(self, trip_id: str, state: Mapping[str, Any]) -> None:
        value = dict(state)
        self._latest[trip_id] = value
        for queue in tuple(self._subscribers.get(trip_id, ())):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(dict(value))

    def unsubscribe(self, trip_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._subscribers.get(trip_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(trip_id, None)


@dataclass
class AppDependencies:
    redis: LifecycleResource
    database: LifecycleResource
    trips: TripRepository
    jobs: JobRepository
    camera_sink: CameraFrameSink
    live_state: LatestStateBroker


def create_test_dependencies() -> AppDependencies:
    return AppDependencies(
        redis=InMemoryHealthResource(),
        database=InMemoryHealthResource(),
        trips=InMemoryTripRepository(),
        jobs=InMemoryJobRepository(),
        camera_sink=InMemoryCameraFrameSink(),
        live_state=InMemoryLatestStateBroker(),
    )


def create_external_dependencies(
    redis_url: str,
    database_url: str,
    *,
    redis_client: AsyncRedisClient | None = None,
    redis_timeout_seconds: float = 2.0,
) -> AppDependencies:
    if redis_client is None:
        from redis.asyncio import Redis

        redis_client = Redis.from_url(redis_url, decode_responses=True)
    redis_repository = RedisJobRepository(
        redis_client,
        timeout_seconds=redis_timeout_seconds,
    )
    return AppDependencies(
        redis=redis_repository,
        database=ConfiguredExternalResource("database", database_url),
        trips=InMemoryTripRepository(),
        jobs=redis_repository,
        camera_sink=InMemoryCameraFrameSink(),
        live_state=InMemoryLatestStateBroker(),
    )
