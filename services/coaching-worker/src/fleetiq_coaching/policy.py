"""Safety-bounded coaching command policy."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fleetiq_contracts import CoachingCommand, RiskEvent


COACHING_LABELS = {
    "compound_risk": ("Compound risk", "Restore attention. Increase distance."),
    "short_ttc": ("Collision risk", "Brake and increase distance."),
    "high_ttc_risk": ("Following distance", "Increase following distance."),
    "moderate_ttc_risk": ("Following distance", "Review following distance."),
    "driver_drowsiness": ("Fatigue coaching", "Stop safely and rest."),
    "driver_distraction": ("Attention coaching", "Restore road attention."),
    "phone_use": ("Phone-use coaching", "Put the phone away."),
    "speeding": ("Speed coaching", "Reduce speed now."),
    "harsh_longitudinal_accel": ("Braking coaching", "Brake more smoothly."),
    "harsh_lateral_accel": ("Cornering coaching", "Reduce corner-entry speed."),
    "lane_departure": ("Lane coaching", "Return to lane safely."),
    "lane_drift": ("Lane coaching", "Center the vehicle."),
}


class CoachingPolicy:
    def command_for(
        self,
        event: RiskEvent,
        *,
        vehicle_id: str,
    ) -> CoachingCommand | None:
        if event.severity < 2:
            return None
        created_at = datetime.now(UTC)
        title, message = COACHING_LABELS.get(
            event.event_type,
            ("Safety coaching", "Review this risk event after the trip."),
        )
        if event.severity >= 5:
            channel = "visual"
            lifetime = 10
        elif event.severity >= 4:
            channel = "visual"
            lifetime = 15
        else:
            channel = "post_trip"
            lifetime = 300
        return CoachingCommand(
            schema_version="1.0",
            command_id=uuid4(),
            event_id=event.event_id,
            correlation_id=event.correlation_id,
            vehicle_id=vehicle_id,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=lifetime),
            channel=channel,
            priority=event.severity,
            title=title,
            message=message,
            dedupe_key=f"{event.trip_id}.{event.frame_index}.{event.event_type}",
        )
