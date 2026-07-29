"""ECS EC2 web/API compute behind a single TLS application load balancer."""

from aws_cdk import CfnOutput, CfnParameter, Fn, Stack, Tags
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        *,
        vpc: ec2.IVpc,
        artifacts_bucket: s3.IBucket,
        database_secret: secretsmanager.ISecret,
        redis_endpoint: str,
        endpoint_arns: dict[str, str],
        environment_name: str,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, stack_id, **kwargs)

        api_image = CfnParameter(
            self,
            "ApiImageUri",
            type="String",
            description="Immutable ECR image URI for FleetIQ API",
        )
        web_image = CfnParameter(
            self,
            "WebImageUri",
            type="String",
            description="Immutable ECR image URI for FleetIQ web",
        )
        certificate_arn = CfnParameter(
            self,
            "CertificateArn",
            type="String",
            description="ACM certificate ARN for the public FleetIQ hostname",
        )
        web_origin = CfnParameter(
            self,
            "WebOrigin",
            type="String",
            description="Public HTTPS origin allowed by the API CORS policy",
        )
        use_in_memory_stores = CfnParameter(
            self,
            "UseInMemoryStores",
            type="String",
            default="true",
            allowed_values=["true", "false"],
            description=(
                "Hackathon bootstrap only; set false after the production "
                "PostgreSQL repository adapter is implemented"
            ),
        )

        self.cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            container_insights_v2=ecs.ContainerInsights.ENABLED,
        )
        capacity = autoscaling.AutoScalingGroup(
            self,
            "Capacity",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            instance_type=ec2.InstanceType("m7i.large"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2023(),
            min_capacity=1,
            max_capacity=3,
        )
        capacity_provider = ecs.AsgCapacityProvider(
            self,
            "CapacityProvider",
            auto_scaling_group=capacity,
            enable_managed_scaling=True,
            enable_managed_termination_protection=False,
        )
        self.cluster.add_asg_capacity_provider(capacity_provider)

        task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sagemaker:InvokeEndpoint"],
                resources=list(endpoint_arns.values()),
            )
        )
        artifacts_bucket.grant_read(task_role, "models/*")
        artifacts_bucket.grant_read_write(task_role, "runtime/*")
        database_secret.grant_read(task_role)

        task_definition = ecs.Ec2TaskDefinition(
            self,
            "TaskDefinition",
            network_mode=ecs.NetworkMode.AWS_VPC,
            task_role=task_role,
        )
        api_logs = logs.LogGroup(
            self,
            "ApiLogs",
            retention=logs.RetentionDays.ONE_MONTH,
        )
        web_logs = logs.LogGroup(
            self,
            "WebLogs",
            retention=logs.RetentionDays.ONE_MONTH,
        )
        endpoint_environment = {
            f"SAGEMAKER_{kind.upper()}_ENDPOINT": Fn.select(
                1, Fn.split("/", endpoint_arn)
            )
            for kind, endpoint_arn in endpoint_arns.items()
        }
        api = task_definition.add_container(
            "api",
            container_name="api",
            image=ecs.ContainerImage.from_registry(api_image.value_as_string),
            cpu=512,
            memory_limit_mib=1024,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="api",
                log_group=api_logs,
            ),
            environment={
                "FLEETIQ_ALLOWED_ORIGINS": web_origin.value_as_string,
                "FLEETIQ_DATABASE_URL": "postgresql://placeholder.invalid/fleetiq",
                "FLEETIQ_REDIS_URL": f"rediss://{redis_endpoint}:6379/0",
                "FLEETIQ_TESTING": use_in_memory_stores.value_as_string,
                **endpoint_environment,
            },
            secrets={
                "FLEETIQ_DATABASE_SECRET_JSON": ecs.Secret.from_secrets_manager(
                    database_secret
                )
            },
        )
        api.add_port_mappings(ecs.PortMapping(container_port=8000))

        web = task_definition.add_container(
            "web",
            container_name="web",
            image=ecs.ContainerImage.from_registry(web_image.value_as_string),
            cpu=512,
            memory_limit_mib=1024,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="web",
                log_group=web_logs,
            ),
            environment={"FLEETIQ_API_BASE_URL": "http://127.0.0.1:8000"},
        )
        web.add_port_mappings(ecs.PortMapping(container_port=3000))
        web.add_container_dependencies(
            ecs.ContainerDependency(
                container=api,
                condition=ecs.ContainerDependencyCondition.START,
            )
        )

        task_security_group = ec2.SecurityGroup(
            self,
            "TaskSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Only the FleetIQ ALB may reach web and API containers",
        )
        self.service = ecs.Ec2Service(
            self,
            "Service",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=1,
            min_healthy_percent=100,
            max_healthy_percent=200,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            security_groups=[task_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        load_balancer = elbv2.ApplicationLoadBalancer(
            self,
            "LoadBalancer",
            vpc=vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )
        certificate = acm.Certificate.from_certificate_arn(
            self,
            "Certificate",
            certificate_arn.value_as_string,
        )
        listener = load_balancer.add_listener(
            "Https",
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[certificate],
            open=True,
        )
        listener.add_targets(
            "WebTargets",
            port=3000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[
                self.service.load_balancer_target(
                    container_name="web",
                    container_port=3000,
                )
            ],
            health_check=elbv2.HealthCheck(path="/", healthy_http_codes="200"),
        )
        listener.add_targets(
            "ApiTargets",
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            priority=10,
            conditions=[
                elbv2.ListenerCondition.path_patterns(["/api/*", "/health/*", "/ws/*"])
            ],
            targets=[
                self.service.load_balancer_target(
                    container_name="api",
                    container_port=8000,
                )
            ],
            health_check=elbv2.HealthCheck(
                path="/health/ready",
                healthy_http_codes="200",
            ),
        )
        api_rule = listener.node.find_child("ApiTargetsRule")
        Tags.of(api_rule).remove("Project")
        Tags.of(api_rule).remove("Environment")
        load_balancer.connections.allow_to(
            task_security_group,
            ec2.Port.tcp(3000),
            "ALB to web",
        )
        load_balancer.connections.allow_to(
            task_security_group,
            ec2.Port.tcp(8000),
            "ALB to API and WebSocket",
        )

        CfnOutput(
            self, "LoadBalancerDnsName", value=load_balancer.load_balancer_dns_name
        )
        Tags.of(self).add("Project", "FleetIQ")
        Tags.of(self).add("Environment", environment_name)
