from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ecs_patterns as ecs_patterns
from constructs import Construct

class AwsCdkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ---- Parámetros por contexto ----
        image_uri = self.node.try_get_context('imageUri')
        container_port = int(self.node.try_get_context('containerPort') or 8000)
        lab_role_arn = self.node.try_get_context('labRoleArn')
        desired_count = int(self.node.try_get_context('desiredCount') or 1)
        cpu = int(self.node.try_get_context('cpu') or 256)
        memory_mib = int(self.node.try_get_context('memoryMiB') or 512)
        use_default_vpc = self.node.try_get_context('useDefaultVpc')

        if not image_uri or not lab_role_arn:
            raise ValueError('Faltan context vars: imageUri y labRoleArn son requeridos.')

        # ---- VPC (usa la VPC por defecto para evitar bootstrap) ----
        if use_default_vpc:
            # Usa la Default VPC (no requiere bootstrap)
            vpc = ec2.Vpc.from_lookup(self, 'DefaultVpc', is_default=True)
        else:
            # Alternativa: crear VPC nueva (requiere bootstrap)
            vpc = ec2.Vpc(
                self, "MyVpc",
                max_azs=2,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="PublicSubnet",
                        subnet_type=ec2.SubnetType.PUBLIC,
                        cidr_mask=24
                    )
                ]
            )

        # ---- Roles (reutiliza LabRole para Task y Execution) ----
        lab_role = iam.Role.from_role_arn(
            self, 'LabRole', 
            lab_role_arn, 
            mutable=False
        )

        # ---- ECS Cluster ----
        cluster = ecs.Cluster(
            self, 'ApiStudentsCluster',
            vpc=vpc,
            cluster_name='api-students-cluster-v2',
            container_insights=True
        )

        # ---- Fargate Service con ALB (patrón) ----
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, 'ApiStudentsService',
            cluster=cluster,
            public_load_balancer=True,
            desired_count=desired_count,
            cpu=cpu,
            memory_limit_mib=memory_mib,
            listener_port=80,
            redirect_http=False,
            assign_public_ip=True,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry(image_uri),
                container_port=container_port,
                container_name='api-students',
                enable_logging=True,
                execution_role=lab_role,
                task_role=lab_role,
                environment={}
            )
        )

        # Health check del Target Group
        fargate_service.target_group.configure_health_check(
            path='/students',
            healthy_http_codes='200-499',
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=5
        )

        # Security Group: permitir HTTP desde Internet
        fargate_service.listener.connections.allow_default_port_from_any_ipv4('Allow HTTP from anywhere')

        # AutoScaling opcional
        scaling = fargate_service.service.auto_scale_task_count(
            min_capacity=desired_count, 
            max_capacity=max(desired_count, 3)
        )
        scaling.scale_on_cpu_utilization(
            'CpuScaling',
            target_utilization_percent=60,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60)
        )

        # Outputs
        CfnOutput(self, 'LoadBalancerDNS', 
                  value=fargate_service.load_balancer.load_balancer_dns_name)
        CfnOutput(self, 'ServiceName', 
                  value=fargate_service.service.service_name)
        CfnOutput(self, 'TargetGroupName', 
                  value=fargate_service.target_group.target_group_name)
