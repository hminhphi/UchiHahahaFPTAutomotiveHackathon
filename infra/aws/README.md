# AWS Infrastructure

AWS CDK v2 definitions for the FleetIQ Guardian deployment target.

## Topology

| Stack | Resources | Network boundary |
| --- | --- | --- |
| Network | VPC, public edge, private compute, isolated data subnets, NAT, S3 endpoint | Only edge subnets are public |
| Data | Versioned S3 artifacts, PostgreSQL RDS, encrypted Redis replication group | RDS and Redis use isolated subnets |
| ML | Detector, depth, lane and DMS SageMaker real-time endpoints | Endpoint ENIs use private compute subnets |
| IoT | Vehicle policy, telemetry rule and CloudWatch log group | FleetIQ topic prefixes only |
| Compute | ALB, ECS cluster/EC2 capacity, co-located web and API task | ALB exposes HTTPS/WSS on port 443 only |

The web and API containers share one ECS task for the hackathon so server-side
web calls use loopback rather than public service discovery. Perception and DMS
models are never loaded into the ECS instances; ECS may invoke only the four
named SageMaker endpoints.

## Parameters

Synthesis creates CloudFormation parameters for:

- Immutable API and web ECR image URIs
- ACM certificate ARN and public web origin
- Four SageMaker inference image URIs
- Four `model.tar.gz` S3 artifact URIs
- Shared SageMaker instance type
- Temporary in-memory store mode

`UseInMemoryStores=true` is the honest hackathon default because the current API
does not yet implement its production PostgreSQL repository adapter. RDS and
Redis are provisioned, secret references are wired into the task definition,
and production promotion is blocked until that adapter and migration job pass.

## Validate

```powershell
uv run --package fleetiq-infra python -m pytest infra/aws/tests -v
pnpm exec cdk synth --app "uv run --package fleetiq-infra python infra/aws/app.py"
```

Set `FLEETIQ_ENVIRONMENT`, `CDK_DEFAULT_ACCOUNT`, and `CDK_DEFAULT_REGION` to
synthesize a named environment. Synthesis is offline with respect to the target
AWS account and does not deploy resources.

## Cost Warning

This definition creates NAT, RDS, Redis, ALB, EC2, and four real-time SageMaker
endpoints. Review the synthesized template, regional GPU quota, and an AWS cost
estimate before deployment. Destroy non-production endpoints immediately after
the judging window.

See [AWS deployment runbook](../../docs/runbooks/aws-deploy.md).
