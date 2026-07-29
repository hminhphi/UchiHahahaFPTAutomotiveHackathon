from __future__ import annotations

import json

from aws_cdk.assertions import Match, Template


def test_network_separates_public_compute_and_data_subnets(
    templates: dict[str, Template],
) -> None:
    network = templates["network"]
    network.resource_count_is("AWS::EC2::VPC", 1)
    network.resource_properties_count_is(
        "AWS::EC2::Subnet",
        {"MapPublicIpOnLaunch": True},
        2,
    )
    network.resource_properties_count_is(
        "AWS::EC2::Subnet",
        {"MapPublicIpOnLaunch": False},
        4,
    )


def test_data_is_private_encrypted_and_not_public(
    templates: dict[str, Template],
) -> None:
    data = templates["data"]
    data.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": Match.any_value(),
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        },
    )
    data.has_resource_properties(
        "AWS::RDS::DBInstance",
        {"PubliclyAccessible": False, "StorageEncrypted": True},
    )
    data.has_resource_properties(
        "AWS::ElastiCache::ReplicationGroup",
        {"AtRestEncryptionEnabled": True, "TransitEncryptionEnabled": True},
    )


def test_compute_uses_ec2_capacity_and_sagemaker_permissions(
    template: Template,
) -> None:
    template.resource_count_is("AWS::ECS::Cluster", 1)
    template.has_resource_properties("AWS::ECS::Service", {"LaunchType": "EC2"})
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": "sagemaker:InvokeEndpoint",
                                "Resource": Match.any_value(),
                            }
                        )
                    ]
                )
            }
        },
    )


def test_compute_exposes_only_https_and_uses_secret_references(
    template: Template,
) -> None:
    template.resource_count_is("AWS::ElasticLoadBalancingV2::Listener", 1)
    template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::Listener",
        {"Port": 443, "Protocol": "HTTPS"},
    )
    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": Match.array_with(
                [
                    Match.object_like(
                        {
                            "Name": "api",
                            "Secrets": Match.array_with(
                                [
                                    Match.object_like(
                                        {"Name": "FLEETIQ_DATABASE_SECRET_JSON"}
                                    )
                                ]
                            ),
                        }
                    )
                ]
            )
        },
    )


def test_compute_has_no_public_task_ip_or_public_application_ports(
    template: Template,
) -> None:
    template.has_resource_properties(
        "AWS::ECS::Service",
        {
            "NetworkConfiguration": {
                "AwsvpcConfiguration": {"AssignPublicIp": "DISABLED"}
            }
        },
    )
    public_ingress: list[tuple[int, int]] = []
    for resource in template.find_resources("AWS::EC2::SecurityGroup").values():
        for rule in resource.get("Properties", {}).get("SecurityGroupIngress", []):
            if rule.get("CidrIp") == "0.0.0.0/0":
                public_ingress.append((rule["FromPort"], rule["ToPort"]))
    assert public_ingress == [(443, 443)]


def test_sagemaker_permission_has_four_non_wildcard_resources(
    template: Template,
) -> None:
    statements = [
        statement
        for policy in template.find_resources("AWS::IAM::Policy").values()
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]
        if statement.get("Action") == "sagemaker:InvokeEndpoint"
    ]
    assert len(statements) == 1
    resources = statements[0]["Resource"]
    assert isinstance(resources, list)
    assert len(resources) == 4
    assert "*" not in resources


def test_ml_stack_creates_four_named_realtime_endpoints(
    templates: dict[str, Template],
) -> None:
    ml = templates["ml"]
    ml.resource_count_is("AWS::SageMaker::Model", 4)
    ml.resource_count_is("AWS::SageMaker::EndpointConfig", 4)
    ml.resource_count_is("AWS::SageMaker::Endpoint", 4)
    ml.has_resource_properties(
        "AWS::SageMaker::Model",
        {"EnableNetworkIsolation": True, "VpcConfig": Match.any_value()},
    )


def test_iot_policy_and_logging_rule_are_bounded(
    templates: dict[str, Template],
) -> None:
    iot = templates["iot"]
    iot.resource_count_is("AWS::IoT::Policy", 1)
    iot.resource_count_is("AWS::IoT::TopicRule", 1)
    iot.resource_count_is("AWS::Logs::LogGroup", 1)
    iot.has_resource_properties(
        "AWS::IoT::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like({"Action": "iot:Connect"}),
                        Match.object_like({"Action": "iot:Publish"}),
                        Match.object_like({"Action": "iot:Subscribe"}),
                        Match.object_like({"Action": "iot:Receive"}),
                    ]
                )
            }
        },
    )


def test_iot_policy_binds_topics_to_the_connected_thing(
    templates: dict[str, Template],
) -> None:
    policies = templates["iot"].find_resources("AWS::IoT::Policy")
    policy_json = json.dumps(next(iter(policies.values())))
    assert "${iot:Connection.Thing.ThingName}" in policy_json
    assert "topic/fleetiq/v1/vehicles/*" not in policy_json
    assert "topicfilter/fleetiq/v1/vehicles/*" not in policy_json


def test_iot_rule_extracts_vehicle_id_from_topic_segment_four(
    templates: dict[str, Template],
) -> None:
    rules = templates["iot"].find_resources("AWS::IoT::TopicRule")
    rule = next(iter(rules.values()))
    sql = rule["Properties"]["TopicRulePayload"]["Sql"]
    assert "topic(4) AS vehicle_id" in sql


def test_every_stack_applies_project_and_environment_tags(
    templates: dict[str, Template],
) -> None:
    tagged_resource_types = {
        "network": "AWS::EC2::VPC",
        "data": "AWS::S3::Bucket",
        "ml": "AWS::SageMaker::Endpoint",
        "iot": "AWS::Logs::LogGroup",
        "compute": "AWS::ECS::Cluster",
    }
    for stack_name, resource_type in tagged_resource_types.items():
        template = templates[stack_name]
        for tag in (
            {"Key": "Project", "Value": "FleetIQ"},
            {"Key": "Environment", "Value": "test"},
        ):
            template.has_resource_properties(
                resource_type,
                {"Tags": Match.array_with([tag])},
            )
