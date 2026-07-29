"""AWS IoT Core ingress policy and bounded telemetry logging."""

from aws_cdk import Aws, Stack, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_iot as iot
from aws_cdk import aws_logs as logs
from constructs import Construct


class IoTStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        *,
        environment_name: str,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, stack_id, **kwargs)

        telemetry_logs = logs.LogGroup(
            self,
            "TelemetryLogs",
            retention=logs.RetentionDays.ONE_MONTH,
        )
        logging_role = iam.Role(
            self,
            "IoTLoggingRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
        )
        telemetry_logs.grant_write(logging_role)

        iot.CfnTopicRule(
            self,
            "TelemetryRule",
            topic_rule_payload=iot.CfnTopicRule.TopicRulePayloadProperty(
                actions=[
                    iot.CfnTopicRule.ActionProperty(
                        cloudwatch_logs=iot.CfnTopicRule.CloudwatchLogsActionProperty(
                            log_group_name=telemetry_logs.log_group_name,
                            role_arn=logging_role.role_arn,
                        )
                    )
                ],
                aws_iot_sql_version="2016-03-23",
                rule_disabled=False,
                sql=(
                    "SELECT *, topic(4) AS vehicle_id "
                    "FROM 'fleetiq/v1/vehicles/+/telemetry'"
                ),
            ),
        )

        thing_name = "${iot:Connection.Thing.ThingName}"
        client_arn = (
            f"arn:{Aws.PARTITION}:iot:{Aws.REGION}:{Aws.ACCOUNT_ID}:client/{thing_name}"
        )
        topic_root = (
            f"arn:{Aws.PARTITION}:iot:{Aws.REGION}:{Aws.ACCOUNT_ID}:"
            f"topic/fleetiq/v1/vehicles/{thing_name}"
        )
        topic_filter_root = (
            f"arn:{Aws.PARTITION}:iot:{Aws.REGION}:{Aws.ACCOUNT_ID}:"
            f"topicfilter/fleetiq/v1/vehicles/{thing_name}"
        )
        iot.CfnPolicy(
            self,
            "VehiclePolicy",
            policy_name=f"fleetiq-{environment_name}-vehicle",
            policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "iot:Connect",
                        "Resource": client_arn,
                        "Condition": {
                            "Bool": {"iot:Connection.Thing.IsAttached": "true"}
                        },
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Publish",
                        "Resource": [
                            f"{topic_root}/telemetry",
                            f"{topic_root}/coaching/ack",
                        ],
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Subscribe",
                        "Resource": f"{topic_filter_root}/coaching/command",
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Receive",
                        "Resource": f"{topic_root}/coaching/command",
                    },
                ],
            },
        )

        Tags.of(self).add("Project", "FleetIQ")
        Tags.of(self).add("Environment", environment_name)
