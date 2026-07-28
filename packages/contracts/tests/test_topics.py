import pytest
from fleetiq_contracts.topics import TopicRegistry


def test_topic_registry_builds_versioned_topics() -> None:
    assert TopicRegistry.risk("trip-a") == "fleetiq/v1/trips/trip-a/risk"
    assert TopicRegistry.coaching_ack("vehicle-a") == (
        "fleetiq/v1/vehicles/vehicle-a/coaching/ack"
    )


@pytest.mark.parametrize("identifier", ["trip/a", "trip+a", "trip#a"])
def test_topic_registry_rejects_mqtt_wildcards_and_separators(identifier: str) -> None:
    """Unsafe segments could alter the topic hierarchy or subscribe to wildcards."""
    with pytest.raises(ValueError):
        TopicRegistry.risk(identifier)
