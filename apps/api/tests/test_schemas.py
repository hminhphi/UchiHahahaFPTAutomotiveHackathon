from datetime import UTC, datetime, timedelta, timezone

import pytest
from fleetiq_api.schemas import AnalysisJob, HealthData, HealthEnvelope
from pydantic import ValidationError


def test_api_envelope_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        HealthEnvelope(
            request_id="request-1",
            correlation_id="correlation-1",
            timestamp=datetime(2026, 7, 29, 12, 0),  # noqa: DTZ001 - invalid fixture
            status="ok",
            data=HealthData(),
        )


def test_api_envelope_normalizes_timestamp_to_rfc3339_utc() -> None:
    envelope = HealthEnvelope(
        request_id="request-1",
        correlation_id="correlation-1",
        timestamp=datetime(2026, 7, 29, 19, 0, tzinfo=timezone(timedelta(hours=7))),
        status="ok",
        data=HealthData(),
    )

    assert envelope.timestamp.tzinfo is UTC
    assert '"timestamp":"2026-07-29T12:00:00Z"' in envelope.model_dump_json()


def test_analysis_job_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError):
        AnalysisJob(
            job_id="job-1",
            trip_id="T01-Sample",
            status="queued",
            idempotency_key="operation-1",
            created_at=datetime(2026, 7, 29, 12, 0),  # noqa: DTZ001 - invalid fixture
        )
