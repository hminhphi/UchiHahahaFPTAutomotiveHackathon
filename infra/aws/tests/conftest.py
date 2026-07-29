from __future__ import annotations

import pytest
from aws_cdk import App
from aws_cdk.assertions import Template
from fleetiq_infra.compute_stack import ComputeStack
from fleetiq_infra.data_stack import DataStack
from fleetiq_infra.iot_stack import IoTStack
from fleetiq_infra.ml_stack import MlStack
from fleetiq_infra.network_stack import NetworkStack


@pytest.fixture(scope="session")
def templates() -> dict[str, Template]:
    app = App()
    network = NetworkStack(app, "FleetIQNetworkTest", environment_name="test")
    data = DataStack(
        app,
        "FleetIQDataTest",
        vpc=network.vpc,
        environment_name="test",
    )
    ml = MlStack(
        app,
        "FleetIQMlTest",
        vpc=network.vpc,
        artifacts_bucket=data.artifacts_bucket,
        environment_name="test",
    )
    iot = IoTStack(app, "FleetIQIoTTest", environment_name="test")
    compute = ComputeStack(
        app,
        "FleetIQComputeTest",
        vpc=network.vpc,
        artifacts_bucket=data.artifacts_bucket,
        database_secret=data.database_secret,
        redis_endpoint=data.redis_endpoint,
        endpoint_arns=ml.endpoint_arns,
        environment_name="test",
    )
    return {
        "network": Template.from_stack(network),
        "data": Template.from_stack(data),
        "ml": Template.from_stack(ml),
        "iot": Template.from_stack(iot),
        "compute": Template.from_stack(compute),
    }


@pytest.fixture(scope="session")
def template(templates: dict[str, Template]) -> Template:
    return templates["compute"]
