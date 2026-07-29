"""Idempotent coaching orchestration."""

from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from fleetiq_contracts import CoachingAck, CoachingCommand, RiskEvent

from .policy import CoachingPolicy


class DeliveryAdapter(Protocol):
    def deliver(self, command: CoachingCommand) -> None: ...


class CoachingWorker:
    def __init__(
        self,
        adapter: DeliveryAdapter,
        *,
        policy: CoachingPolicy | None = None,
    ) -> None:
        self.adapter = adapter
        self.policy = policy or CoachingPolicy()
        self._acknowledgements: dict[str, CoachingAck] = {}

    def process(self, event: RiskEvent, *, vehicle_id: str) -> CoachingAck | None:
        command = self.policy.command_for(event, vehicle_id=vehicle_id)
        if command is None:
            return None
        existing = self._acknowledgements.get(command.dedupe_key)
        if existing is not None:
            return existing.model_copy(deep=True)
        self.adapter.deliver(command)
        acknowledgement = CoachingAck(
            schema_version="1.0",
            ack_id=uuid4(),
            command_id=command.command_id,
            correlation_id=command.correlation_id,
            vehicle_id=command.vehicle_id,
            acknowledged_at=datetime.now(UTC),
            status="accepted",
        )
        self._acknowledgements[command.dedupe_key] = acknowledgement
        return acknowledgement.model_copy(deep=True)
