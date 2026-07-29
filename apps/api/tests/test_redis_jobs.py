import asyncio
import json
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from fleetiq_api.dependencies import (
    AppDependencies,
    IdempotencyConflictError,
    InMemoryCameraFrameSink,
    InMemoryHealthResource,
    InMemoryLatestStateBroker,
    InMemoryTripRepository,
    JobRepositoryUnavailableError,
    RedisJobRepository,
    create_external_dependencies,
)
from fleetiq_api.main import create_app
from fleetiq_api.schemas import AnalysisJobCreate


@dataclass
class FakeRedisServer:
    values: dict[str, str] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class FakeRedisClient:
    """Implements the Redis commands used by the repository with atomic EVAL."""

    def __init__(
        self,
        server: FakeRedisServer,
        *,
        command_delay: float = 0,
        ping_result: bool = True,
    ) -> None:
        self.server = server
        self.command_delay = command_delay
        self.ping_result = ping_result
        self.closed = False
        self.eval_calls = 0

    async def eval(self, script: str, numkeys: int, *values: str) -> list[str]:
        assert "redis.call" in script
        assert numkeys == 2
        await asyncio.sleep(self.command_delay)
        idempotency_key, job_key, fingerprint, idempotency_json, job_json = values
        async with self.server.lock:
            self.eval_calls += 1
            existing = self.server.values.get(idempotency_key)
            if existing is not None:
                existing_payload = json.loads(existing)
                status = "existing" if existing_payload["fingerprint"] == fingerprint else "conflict"
                return [status, existing]
            self.server.values[idempotency_key] = idempotency_json
            self.server.values[job_key] = job_json
            return ["created", idempotency_json]

    async def get(self, key: str) -> str | None:
        await asyncio.sleep(self.command_delay)
        return self.server.values.get(key)

    async def ping(self) -> bool:
        await asyncio.sleep(self.command_delay)
        return self.ping_result

    async def aclose(self) -> None:
        self.closed = True


def test_redis_repository_atomically_deduplicates_concurrent_submissions() -> None:
    async def scenario() -> tuple[set[str], int]:
        client = FakeRedisClient(FakeRedisServer(), command_delay=0.001)
        repository = RedisJobRepository(client, timeout_seconds=0.2)
        await repository.start()
        command = AnalysisJobCreate(trip_id="T01-Sample")
        jobs = await asyncio.gather(
            *(repository.create(command, idempotency_key="same-operation") for _ in range(20))
        )
        return {job.job_id for job in jobs}, client.eval_calls

    job_ids, calls = asyncio.run(scenario())

    assert job_ids == {next(iter(job_ids))}
    assert calls == 20


def test_redis_repository_survives_client_restart_and_detects_conflict() -> None:
    async def scenario() -> tuple[str, str]:
        server = FakeRedisServer()
        first_client = FakeRedisClient(server)
        first_repository = RedisJobRepository(first_client, timeout_seconds=0.2)
        await first_repository.start()
        first = await first_repository.create(
            AnalysisJobCreate(trip_id="T01-Sample"),
            idempotency_key="persistent-operation",
        )
        await first_repository.close()

        second_repository = RedisJobRepository(FakeRedisClient(server), timeout_seconds=0.2)
        await second_repository.start()
        repeated = await second_repository.create(
            AnalysisJobCreate(trip_id="T01-Sample"),
            idempotency_key="persistent-operation",
        )
        with pytest.raises(IdempotencyConflictError):
            await second_repository.create(
                AnalysisJobCreate(trip_id="T02-Sample"),
                idempotency_key="persistent-operation",
            )
        loaded = await second_repository.get(first.job_id)
        assert loaded is not None
        return repeated.job_id, loaded.job_id

    repeated_id, loaded_id = asyncio.run(scenario())

    assert repeated_id == loaded_id


def test_redis_repository_bounds_failures_and_readiness() -> None:
    async def scenario() -> tuple[bool, float]:
        client = FakeRedisClient(FakeRedisServer(), command_delay=0.05)
        repository = RedisJobRepository(client, timeout_seconds=0.001)
        await repository.start()
        loop = asyncio.get_running_loop()
        started = loop.time()
        ready = await repository.ready()
        with pytest.raises(JobRepositoryUnavailableError):
            await repository.create(
                AnalysisJobCreate(trip_id="T01-Sample"),
                idempotency_key="timed-out-operation",
            )
        return ready, loop.time() - started

    ready, elapsed = asyncio.run(scenario())

    assert ready is False
    assert elapsed < 0.1


def test_production_dependencies_use_redis_repository() -> None:
    redis_client = FakeRedisClient(FakeRedisServer())

    dependencies = create_external_dependencies(
        "redis://cache:6379/0",
        "postgresql://db/fleetiq",
        redis_client=redis_client,
        redis_timeout_seconds=0.2,
    )

    assert isinstance(dependencies.jobs, RedisJobRepository)
    assert dependencies.redis is dependencies.jobs


def test_lifespan_closes_redis_client() -> None:
    redis_client = FakeRedisClient(FakeRedisServer())
    repository = RedisJobRepository(redis_client, timeout_seconds=0.2)
    dependencies = AppDependencies(
        redis=repository,
        database=InMemoryHealthResource(),
        trips=InMemoryTripRepository(),
        jobs=repository,
        camera_sink=InMemoryCameraFrameSink(),
        live_state=InMemoryLatestStateBroker(),
    )

    with TestClient(create_app(testing=True, dependencies=dependencies)):
        assert redis_client.closed is False

    assert redis_client.closed is True


def test_job_route_maps_redis_failure_to_stable_503() -> None:
    redis_client = FakeRedisClient(FakeRedisServer(), command_delay=0.05)
    repository = RedisJobRepository(redis_client, timeout_seconds=0.001)
    dependencies = AppDependencies(
        redis=repository,
        database=InMemoryHealthResource(),
        trips=InMemoryTripRepository(),
        jobs=repository,
        camera_sink=InMemoryCameraFrameSink(),
        live_state=InMemoryLatestStateBroker(),
    )

    with TestClient(create_app(testing=True, dependencies=dependencies)) as client:
        response = client.post(
            "/api/v1/jobs",
            json={"trip_id": "T01-Sample"},
            headers={"Idempotency-Key": "unavailable-operation"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "job_repository_unavailable"
