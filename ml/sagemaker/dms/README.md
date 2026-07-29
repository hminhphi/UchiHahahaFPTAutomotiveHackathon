# DMS SageMaker Handler

CPU-safe SageMaker inference-toolkit functions for the DMS endpoint. The
handler accepts a versioned JSON `InferenceRequest`, invokes a model exposing
`predict(request)`, and returns a correlated `InferenceResponse`.

`model_fn` loads an optional `dms_model.json` fixed-output fallback for
deployment smoke tests. Production model packaging can replace that object
without changing the request/response boundary.
