"""Transparent bounded safety scoring."""

from dataclasses import dataclass
from typing import Literal

DriverStateName = Literal["attentive", "distracted", "drowsy", "unknown"]


@dataclass(frozen=True)
class RiskScore:
    score: int
    severity: int
    explanation_codes: list[str]
    penalties: dict[str, int]


class RiskScorer:
    def score(
        self,
        *,
        ttc_s: float | None,
        driver_state: DriverStateName,
        phone_use: bool | None = None,
        speed_mps: float,
        lane_offset_m: float | None,
        speed_limit_mps: float | None = None,
        longitudinal_accel_mps2: float | None = None,
        lateral_accel_mps2: float | None = None,
    ) -> RiskScore:
        if speed_mps < 0:
            raise ValueError("speed cannot be negative")
        codes: list[str] = []

        collision_penalty = 0
        severity = 1
        if ttc_s is not None:
            if ttc_s <= 0:
                raise ValueError("TTC must be positive")
            if ttc_s < 1.5:
                collision_penalty, severity = 35, 4
                codes.append("short_ttc")
            elif ttc_s < 2.5:
                collision_penalty, severity = 26, 3
                codes.append("high_ttc_risk")
            elif ttc_s < 4.0:
                collision_penalty, severity = 15, 2
                codes.append("moderate_ttc_risk")

        attention_penalty = 0
        if driver_state == "drowsy":
            attention_penalty = 25
            codes.append("driver_drowsiness")
            severity = max(severity, 3)
        elif driver_state == "distracted":
            attention_penalty = 15
            codes.append("driver_distraction")
            severity = max(severity, 2)

        if phone_use is True:
            attention_penalty = max(attention_penalty, 15)
            codes.append("phone_use")
            severity = max(severity, 2)

        if collision_penalty and attention_penalty:
            severity = min(5, severity + 1)
            codes.append("compound_risk")

        handling_penalty = 0
        if speed_limit_mps is not None:
            if speed_limit_mps <= 0:
                raise ValueError("speed limit must be positive")
            if speed_mps > speed_limit_mps:
                handling_penalty += min(
                    15,
                    max(5, round((speed_mps / speed_limit_mps - 1) * 30)),
                )
                codes.append("speeding")
                severity = max(severity, 2)
        if longitudinal_accel_mps2 is not None and abs(longitudinal_accel_mps2) >= 4.0:
            handling_penalty += 10
            codes.append("harsh_longitudinal_accel")
            severity = max(severity, 2)
        if lateral_accel_mps2 is not None and abs(lateral_accel_mps2) >= 3.0:
            handling_penalty += 10
            codes.append("harsh_lateral_accel")
            severity = max(severity, 2)
        handling_penalty = min(25, handling_penalty)

        lane_penalty = 0
        if lane_offset_m is not None:
            offset = abs(lane_offset_m)
            if offset >= 0.75:
                lane_penalty = 15
                codes.append("lane_departure")
                severity = max(severity, 3)
            elif offset >= 0.4:
                lane_penalty = 8
                codes.append("lane_drift")
                severity = max(severity, 2)

        penalties = {
            "collision": collision_penalty,
            "attention": attention_penalty,
            "handling": handling_penalty,
            "lane": lane_penalty,
        }
        return RiskScore(
            score=max(0, 100 - sum(penalties.values())),
            severity=severity,
            explanation_codes=codes,
            penalties=penalties,
        )
