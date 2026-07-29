# FleetIQ Model Clients

Typed adapters connect FleetIQ workers to deterministic local fixtures or
Amazon SageMaker realtime endpoints. Both adapters consume the versioned
`fleetiq_contracts.InferenceRequest` contract and return
`fleetiq_contracts.InferenceResponse`.

## Local development

The base package has no AWS dependency:

```powershell
uv run --package fleetiq-model-clients pytest packages/model-clients/tests -v
```

Use `LocalFixtureModelClient.from_fixture(...)` in unit tests, Compose mocks,
and offline demos.

## SageMaker workers

Install the AWS extra in ECS worker images:

```powershell
uv sync --package fleetiq-model-clients --extra aws
```

Select the endpoint by role. There is no generic endpoint fallback:

```text
SAGEMAKER_DETECTOR_ENDPOINT
SAGEMAKER_DEPTH_ENDPOINT
SAGEMAKER_LANE_ENDPOINT
SAGEMAKER_DMS_ENDPOINT
```

`SageMakerModelClient.from_environment(EndpointKind.DETECTOR)` creates a
`sagemaker-runtime` client with a 3-second connect timeout, a 30-second read
timeout, and at most three total attempts. Typed requests are sent as
`application/json`. `infer_bytes(...)` is available for direct JPEG or tensor
payloads.

Adapter exceptions deliberately omit response bodies, authorization values,
AWS exception messages, and URL query strings. Callers should log only the
sanitized adapter exception. Typed `infer(request)` calls also require the
response to match the request's ID, correlation ID, trip, frame, and timestamp
instant; a mismatched response raises `SageMakerResponseIdentityError` without
including response values.
