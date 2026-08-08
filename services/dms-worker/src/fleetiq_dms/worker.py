"""Typed DMS inference orchestration with Solution 2 Two-Stage Bi-LSTM support."""

from __future__ import annotations

from collections.abc import Callable

from fleetiq_contracts import InferenceRequest, InferenceResponse
from fleetiq_contracts.inference import DriverState
from fleetiq_model_clients.base import ModelClient

from .predictor import TwoStagePredictor
from .smoothing import StateSmoother


class DmsWorker:
    def __init__(
        self,
        client: ModelClient,
        *,
        predictor: TwoStagePredictor | None = None,
        window_size: int = 5,
        min_votes: int = 3,
        publish: Callable[[InferenceResponse], None] | None = None,
    ) -> None:
        StateSmoother(window_size=window_size, min_votes=min_votes)
        self._client = client
        self._predictor = predictor
        self._window_size = window_size
        self._min_votes = min_votes
        self._smoothers: dict[str, StateSmoother] = {}
        self._publish = publish

    def process(self, request: InferenceRequest) -> InferenceResponse:
        if request.camera_view != "driver":
            raise ValueError("DMS worker requires the driver camera view")

        response = self._client.infer(request)
        if response.driver_state is None:
            raise ValueError("DMS response requires driver_state")

        # Apply smoothing
        smoother = self._smoothers.setdefault(
            request.trip_id,
            StateSmoother(
                window_size=self._window_size,
                min_votes=self._min_votes,
            ),
        )
        smoothed_state = smoother.update(response.driver_state.state)
        state_values = response.driver_state.model_dump()
        state_values["state"] = smoothed_state
        if smoothed_state != response.driver_state.state:
            state_values["confidence"] = 0.0

        values = response.model_dump()
        values["driver_state"] = DriverState.model_validate(state_values)
        result = InferenceResponse.model_validate(values)
        if self._publish is not None:
            self._publish(result)
        return result
