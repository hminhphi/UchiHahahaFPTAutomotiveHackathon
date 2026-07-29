"""Safety-bounded coaching command policy."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fleetiq_contracts import CoachingCommand, RiskEvent


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
        if event.severity >= 5:
            channel = "visual"
            title = "Collision risk"
            message = "Brake now. Increase distance."
            lifetime = 10
        elif event.severity >= 4:
            channel = "visual"
            title = "High risk"
            message = "Slow down and increase following distance."
            lifetime = 15
        else:
            channel = "post_trip"
            title = "Safety coaching"
            message = "Review this risk event after the trip."
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
