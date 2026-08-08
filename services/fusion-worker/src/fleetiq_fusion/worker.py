"""Road, DMS, and telemetry fusion orchestration."""

from datetime import UTC, datetime
from uuid import uuid4

from fleetiq_contracts import InferenceResponse, RiskEvent, TelemetryEvent

from .alignment import SignalAligner
from .scoring import RiskScorer


class FusionWorker:
    def __init__(
        self,
        *,
        scorer: RiskScorer | None = None,
        aligner: SignalAligner | None = None,
    ) -> None:
        self._scorer = scorer or RiskScorer()
        self._aligner = aligner or SignalAligner()

    def fuse(
        self,
        road: InferenceResponse,
        dms: InferenceResponse,
        telemetry: TelemetryEvent,
    ) -> RiskEvent:
        self._aligner.validate(road, dms, telemetry)
        if dms.driver_state is None:
            raise ValueError("DMS input requires driver_state")
        ttc_values = [
            detection.ttc_s
            for detection in road.detections
            if detection.ttc_s is not None
        ]
        ttc_s = min(ttc_values) if ttc_values else None
        lane_offset = road.lane_state.lane_offset_m if road.lane_state else None
        score = self._scorer.score(
            ttc_s=ttc_s,
            driver_state=dms.driver_state.state,
            phone_use=dms.driver_state.phone_use,
            speed_mps=telemetry.speed_mps or 0.0,
            speed_limit_mps=telemetry.speed_limit_mps,
            longitudinal_accel_mps2=telemetry.longitudinal_accel_mps2,
            lateral_accel_mps2=telemetry.lateral_accel_mps2,
            lane_offset_m=lane_offset,
        )
        codes = score.explanation_codes
        confidence_values = [dms.driver_state.confidence]
        confidence_values.extend(
            detection.confidence for detection in road.detections
        )
        if road.lane_state is not None:
            confidence_values.append(road.lane_state.confidence)
        event_type = (
            "compound_risk"
            if "compound_risk" in codes
            else (codes[0] if codes else "risk_assessment")
        )
        return RiskEvent(
            schema_version="1.0",
            event_id=uuid4(),
            correlation_id=road.correlation_id,
            trip_id=road.trip_id,
            frame_index=max(
                road.frame_index,
                dms.frame_index,
                telemetry.frame_index,
            ),
            producer="fusion-worker",
            occurred_at=datetime.now(UTC),
            event_type=event_type,
            severity=score.severity,
            confidence=min(confidence_values),
            explanation=", ".join(codes) if codes else "no elevated risk",
        )
