# AWS Deployment Runbook

This runbook prepares FleetIQ for ECS EC2 plus SageMaker. The current task
validates and synthesizes infrastructure only; it does not authorize a deploy.

## 1. Release Gates

Confirm all of the following before creating cloud resources:

- The target account and region are approved.
- AWS CDK is bootstrapped in that account and region.
- The regional quota supports four instances of the selected SageMaker type.
- An ACM certificate exists in the deployment region for the FleetIQ hostname.
- Route 53 or the external DNS provider can point the hostname to the ALB.
- API and web images are immutable ECR digests, not mutable `latest` tags.
- The web image was built with
  `NEXT_PUBLIC_WS_BASE_URL=wss://<FleetIQ-host>`; this public value is compiled
  by Next.js and cannot be corrected only through ECS runtime environment.
- Detector, depth, lane, and DMS model archives are immutable S3 object versions.
- AWS Budgets and cost alerts are enabled.
- `UseInMemoryStores=false` is prohibited until the PostgreSQL adapter,
  migrations, persistence tests, and rollback migration are complete.

## 2. Local Preflight

```powershell
$env:FLEETIQ_ENVIRONMENT = "dev"
$env:CDK_DEFAULT_ACCOUNT = "<account-id>"
$env:CDK_DEFAULT_REGION = "ap-southeast-1"

uv lock --check
uv run --package fleetiq-infra python -m pytest infra/aws/tests -v
pnpm install --frozen-lockfile
pnpm exec cdk synth --app "uv run --package fleetiq-infra python infra/aws/app.py"
```

Inspect `cdk.out` for:

- No public IP on ECS, RDS, Redis, or SageMaker ENIs
- One public listener using HTTPS on port 443
- ECS service `LaunchType` set to `EC2`
- `sagemaker:InvokeEndpoint` restricted to four FleetIQ endpoint ARNs
- S3 access restricted to `models/*` and `runtime/*`
- Database credentials referenced from Secrets Manager
- `Project=FleetIQ` and the expected `Environment` tags

Do not commit `cdk.out`.

## 3. Publish Containers And Models

Build API and web images from the repository root, scan them, then push immutable
digests to ECR. Pass
`--build-arg NEXT_PUBLIC_WS_BASE_URL=wss://<FleetIQ-host>` to the web build.
Build each SageMaker inference image from its handler directory, run the local
handler tests, scan it, and push it to ECR.

Package each model as `model.tar.gz` using its pinned preprocessing,
postprocessing, class map, and calibration metadata. Upload under:

```text
s3://<artifacts-bucket>/models/detector/<version>/model.tar.gz
s3://<artifacts-bucket>/models/depth/<version>/model.tar.gz
s3://<artifacts-bucket>/models/lane/<version>/model.tar.gz
s3://<artifacts-bucket>/models/dms/<version>/model.tar.gz
```

Record image digests, S3 object versions, dataset version, metrics, owner, and
rollback version in the release ticket.

## 4. Deployment Order

Use CI with an assumed deployment role and manual approval:

1. Network stack
2. Data stack
3. ML stack
4. IoT stack
5. Compute stack
6. DNS alias to the ALB after health checks pass

Supply the CloudFormation parameters emitted by synth. Keep the ACM certificate
ARN and public web origin environment-specific. The web origin must be the exact
HTTPS origin, without a path or wildcard.

For the hackathon environment, use `UseInMemoryStores=true` and label the
dashboard as non-persistent. Do not claim RDS-backed durability. Production
deployment remains blocked by the repository adapter gate above.

## 5. Post-Deploy Verification

Verify:

```text
GET https://<host>/health/live
GET https://<host>/health/ready
GET https://<host>/
WSS https://<host>/ws/v1/trips/<trip>/camera/road_left
```

Then run one synthetic trip:

- Publish signed telemetry through AWS IoT Core.
- Confirm the IoT rule writes to the expected CloudWatch log group.
- Invoke each named SageMaker endpoint with a bounded canary request.
- Confirm one camera WebSocket frame is accepted.
- Confirm one risk event reaches the dashboard.
- Confirm one coaching command is acknowledged by the CarSky mock bridge.

Check ALB 5xx, ECS task restarts, endpoint model latency/errors, RDS connections,
Redis errors, and log redaction before exposing the demo.

## 6. Rollback

For application regression:

1. Stop DNS promotion.
2. Restore the prior ECS task-definition revision.
3. Wait for ALB target health and run the smoke path.

For model regression:

1. Restore the prior endpoint configuration and model artifact version.
2. Wait until the endpoint is `InService`.
3. Run the fixed canary frame set and compare outputs.

For infrastructure regression, use the previously approved CloudFormation
change set. Never delete RDS or the artifact bucket as a rollback shortcut.

## 7. Shutdown

After judging, scale or remove non-production SageMaker endpoints first because
they are the dominant idle cost. Then remove ECS capacity, NAT, Redis, RDS, and
the ALB through the approved CDK/CloudFormation path. Retain model artifacts,
release metadata, and database snapshots according to the project retention
decision.
