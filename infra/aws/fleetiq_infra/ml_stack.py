"""Private SageMaker real-time endpoints for FleetIQ perception models."""

from aws_cdk import Aws, CfnParameter, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct

ENDPOINT_KINDS = ("detector", "depth", "lane", "dms")


class MlStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        *,
        vpc: ec2.IVpc,
        artifacts_bucket: s3.IBucket,
        environment_name: str,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, stack_id, **kwargs)

        execution_role = iam.Role(
            self,
            "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
        )
        artifacts_bucket.grant_read(execution_role, "models/*")
        endpoint_security_group = ec2.SecurityGroup(
            self,
            "EndpointSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Outbound-only SageMaker endpoint interfaces",
        )
        subnet_ids = vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        ).subnet_ids
        instance_type = CfnParameter(
            self,
            "InferenceInstanceType",
            type="String",
            default="ml.g5.xlarge",
            description="Shared real-time endpoint instance type",
        )

        self.endpoint_arns: dict[str, str] = {}
        for kind in ENDPOINT_KINDS:
            title = kind.title()
            image_uri = CfnParameter(
                self,
                f"{title}ImageUri",
                type="String",
                description=f"ECR image URI for the {kind} inference container",
            )
            model_artifact_uri = CfnParameter(
                self,
                f"{title}ModelArtifactUri",
                type="String",
                description=f"S3 model.tar.gz URI for the {kind} model",
            )
            model = sagemaker.CfnModel(
                self,
                f"{title}Model",
                execution_role_arn=execution_role.role_arn,
                enable_network_isolation=True,
                primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                    image=image_uri.value_as_string,
                    model_data_url=model_artifact_uri.value_as_string,
                    environment={"FLEETIQ_MODEL_KIND": kind},
                ),
                vpc_config=sagemaker.CfnModel.VpcConfigProperty(
                    security_group_ids=[endpoint_security_group.security_group_id],
                    subnets=subnet_ids,
                ),
            )
            endpoint_config = sagemaker.CfnEndpointConfig(
                self,
                f"{title}EndpointConfig",
                production_variants=[
                    sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                        initial_instance_count=1,
                        instance_type=instance_type.value_as_string,
                        model_name=model.attr_model_name,
                        variant_name="primary",
                    )
                ],
            )
            endpoint_name = f"fleetiq-{environment_name}-{kind}"
            endpoint = sagemaker.CfnEndpoint(
                self,
                f"{title}Endpoint",
                endpoint_config_name=endpoint_config.attr_endpoint_config_name,
                endpoint_name=endpoint_name,
            )
            endpoint.add_resource_dependency(endpoint_config)
            self.endpoint_arns[kind] = Stack.of(self).format_arn(
                service="sagemaker",
                region=Aws.REGION,
                account=Aws.ACCOUNT_ID,
                resource="endpoint",
                resource_name=endpoint_name,
            )

        Tags.of(self).add("Project", "FleetIQ")
        Tags.of(self).add("Environment", environment_name)
