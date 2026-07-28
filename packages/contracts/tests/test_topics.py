import pytest
from fleetiq_contracts.topics import TopicRegistry


def test_topic_registry_builds_versioned_topics() -> None:
    assert TopicRegistry.risk("trip-a") == "fleetiq/v1/trips/trip-a/risk"
    assert TopicRegistry.coaching_ack("vehicle-a") == (
        "fleetiq/v1/vehicles/vehicle-a/coaching/ack"
    )


@pytest.mark.parametrize(
    ("builder", "identifier", "expected"),
    [
        (TopicRegistry.telemetry, "vehicle-a", "fleetiq/v1/vehicles/vehicle-a/telemetry"),
        (TopicRegistry.risk, "trip-a", "fleetiq/v1/trips/trip-a/risk"),
        (
            TopicRegistry.coaching_command,
            "vehicle-a",
            "fleetiq/v1/vehicles/vehicle-a/coaching/command",
        ),
        (
            TopicRegistry.coaching_ack,
            "vehicle-a",
            "fleetiq/v1/vehicles/vehicle-a/coaching/ack",
        ),
        (TopicRegistry.service_status, "fusion-worker", "fleetiq/v1/services/fusion-worker/status"),
        (TopicRegistry.dead_letter, "roadface-worker", "fleetiq/v1/dead-letter/roadface-worker"),
    ],
)
def test_topic_registry_builds_every_supported_route(
    builder: object, identifier: str, expected: str
) -> None:
    """Changing a route builder would break its corresponding MQTT consumer."""
    assert builder(identifier) == expected


@pytest.mark.parametrize("identifier", ["trip/a", "trip+a", "trip#a"])
def test_topic_registry_rejects_mqtt_wildcards_and_separators(identifier: str) -> None:
    """Unsafe segments could alter the topic hierarchy or subscribe to wildcards."""
    with pytest.raises(ValueError):
        TopicRegistry.risk(identifier)
