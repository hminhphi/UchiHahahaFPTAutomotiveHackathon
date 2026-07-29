# FleetIQ DMS Worker

Consumes versioned driver-camera `InferenceRequest` records, invokes the
configured DMS model client, smooths state independently per trip, and emits a
versioned `InferenceResponse`.

States are `attentive`, `distracted`, `drowsy`, and `unknown`. Configure
`SAGEMAKER_DMS_ENDPOINT`, `FLEETIQ_DMS_WINDOW_SIZE`, and
`FLEETIQ_DMS_MIN_VOTES`.

The CLI accepts one JSON request per stdin line and writes one JSON response per
line. Production orchestration can call the same `DmsWorker.process` boundary.
