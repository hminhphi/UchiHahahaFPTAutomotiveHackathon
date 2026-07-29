"""Encrypted FleetIQ object, relational, and cache data services."""

from aws_cdk import Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticache as elasticache
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from constructs import Construct


class DataStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        *,
        vpc: ec2.IVpc,
        environment_name: str,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, stack_id, **kwargs)

        self.artifacts_bucket = s3.Bucket(
            self,
            "Artifacts",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        database_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            allow_all_outbound=False,
            description="PostgreSQL access from private FleetIQ workloads",
        )
        database_security_group.add_ingress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(5432),
            "Private VPC PostgreSQL clients",
        )
        self.database = rds.DatabaseInstance(
            self,
            "Database",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_13
            ),
            credentials=rds.Credentials.from_generated_secret("fleetiq_admin"),
            database_name="fleetiq",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,
                ec2.InstanceSize.SMALL,
            ),
            allocated_storage=30,
            max_allocated_storage=100,
            storage_encrypted=True,
            multi_az=False,
            publicly_accessible=False,
            backup_retention=Duration.days(7),
            deletion_protection=environment_name == "prod",
            removal_policy=RemovalPolicy.SNAPSHOT,
            security_groups=[database_security_group],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
        )
        if self.database.secret is None:
            raise ValueError("RDS generated credentials must expose a secret")
        self.database_secret = self.database.secret

        isolated_subnets = vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
        ).subnet_ids
        cache_subnets = elasticache.CfnSubnetGroup(
            self,
            "CacheSubnets",
            description="FleetIQ isolated Redis subnets",
            subnet_ids=isolated_subnets,
        )
        cache_security_group = ec2.SecurityGroup(
            self,
            "CacheSecurityGroup",
            vpc=vpc,
            allow_all_outbound=False,
            description="Redis access from private FleetIQ workloads",
        )
        cache_security_group.add_ingress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(6379),
            "Private VPC Redis clients",
        )
        cache = elasticache.CfnReplicationGroup(
            self,
            "Redis",
            replication_group_description="FleetIQ durable job and live-state cache",
            at_rest_encryption_enabled=True,
            transit_encryption_enabled=True,
            automatic_failover_enabled=False,
            cache_node_type="cache.t4g.small",
            engine="redis",
            engine_version="7.1",
            num_cache_clusters=1,
            cache_subnet_group_name=cache_subnets.ref,
            security_group_ids=[cache_security_group.security_group_id],
        )
        cache.add_resource_dependency(cache_subnets)
        self.redis_endpoint = cache.attr_primary_end_point_address

        Tags.of(self).add("Project", "FleetIQ")
        Tags.of(self).add("Environment", environment_name)
