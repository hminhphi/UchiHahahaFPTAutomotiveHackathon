"""FleetIQ CDK application entrypoint. Synthesis never performs a deployment."""

from __future__ import annotations

import os

from aws_cdk import App, Environment
from fleetiq_infra import ComputeStack, DataStack, IoTStack, MlStack, NetworkStack


def main() -> None:
    app = App()
    environment_name = app.node.try_get_context("environment") or os.getenv(
        "FLEETIQ_ENVIRONMENT", "dev"
    )
    target = Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    )

    network = NetworkStack(
        app,
        f"FleetIQ-{environment_name}-Network",
        environment_name=environment_name,
        env=target,
    )
    data = DataStack(
        app,
        f"FleetIQ-{environment_name}-Data",
        vpc=network.vpc,
        environment_name=environment_name,
        env=target,
    )
    ml = MlStack(
        app,
        f"FleetIQ-{environment_name}-Ml",
        vpc=network.vpc,
        artifacts_bucket=data.artifacts_bucket,
        environment_name=environment_name,
        env=target,
    )
    iot = IoTStack(
        app,
        f"FleetIQ-{environment_name}-IoT",
        environment_name=environment_name,
        env=target,
    )
    compute = ComputeStack(
        app,
        f"FleetIQ-{environment_name}-Compute",
        vpc=network.vpc,
        artifacts_bucket=data.artifacts_bucket,
        database_secret=data.database_secret,
        redis_endpoint=data.redis_endpoint,
        endpoint_arns=ml.endpoint_arns,
        environment_name=environment_name,
        env=target,
    )
    data.add_stack_dependency(network)
    ml.add_stack_dependency(network)
    ml.add_stack_dependency(data)
    compute.add_stack_dependency(network)
    compute.add_stack_dependency(data)
    compute.add_stack_dependency(ml)
    iot.add_stack_dependency(network)
    app.synth()


if __name__ == "__main__":
    main()
