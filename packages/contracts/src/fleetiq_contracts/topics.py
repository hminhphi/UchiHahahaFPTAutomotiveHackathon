"""The sole constructor for FleetIQ's versioned MQTT topics."""

from .base import validate_mqtt_segment


class TopicRegistry:
    """Build MQTT topics from safe identifier segments."""

    _ROOT = "fleetiq/v1"

    @classmethod
    def telemetry(cls, vehicle_id: str) -> str:
        return f"{cls._ROOT}/vehicles/{validate_mqtt_segment(vehicle_id)}/telemetry"

    @classmethod
    def risk(cls, trip_id: str) -> str:
        return f"{cls._ROOT}/trips/{validate_mqtt_segment(trip_id)}/risk"

    @classmethod
    def coaching_command(cls, vehicle_id: str) -> str:
        return f"{cls._ROOT}/vehicles/{validate_mqtt_segment(vehicle_id)}/coaching/command"

    @classmethod
    def coaching_ack(cls, vehicle_id: str) -> str:
        return f"{cls._ROOT}/vehicles/{validate_mqtt_segment(vehicle_id)}/coaching/ack"

    @classmethod
    def service_status(cls, service: str) -> str:
        return f"{cls._ROOT}/services/{validate_mqtt_segment(service)}/status"

    @classmethod
    def dead_letter(cls, source: str) -> str:
        return f"{cls._ROOT}/dead-letter/{validate_mqtt_segment(source)}"
