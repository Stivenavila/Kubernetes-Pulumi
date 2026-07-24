"""
AWS EKS Cluster with Pulumi
Production-ready Kubernetes cluster on AWS with VPC, networking, and node groups
"""

import pulumi
import pulumi_aws as aws
import pulumi_eks as eks
from pulumi import Output, ResourceOptions

# Get configuration values
config = pulumi.Config()
cluster_name = config.get("clusterName") or "eks-cluster"
cluster_version = config.get("clusterVersion") or "1.29"
desired_capacity = config.get_int("desiredCapacity") or 2
min_size = config.get_int("minSize") or 1
max_size = config.get_int("maxSize") or 4
instance_type = config.get("instanceType") or "t3.medium"
vpc_cidr = config.get("vpcCidr") or "10.0.0.0/16"

# Tags for all resources
common_tags = {
    "Project": "EKS-Cluster",
    "ManagedBy": "Pulumi",
    "Environment": pulumi.get_stack(),
}

# Get available AZs
available_azs = aws.get_availability_zones(state="available")
az_names = available_azs.names[:3]  # Use first 3 AZs

print(f"Creating EKS cluster '{cluster_name}' in AZs: {az_names}")

# ============================================================================
# VPC and Networking
# ============================================================================

# Create VPC
vpc = aws.ec2.Vpc(
    "eks-vpc",
    cidr_block=vpc_cidr,
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={**common_tags, "Name": f"{cluster_name}-vpc"},
)

# Internet Gateway for public subnets
igw = aws.ec2.InternetGateway(
    "eks-igw",
    vpc_id=vpc.id,
    tags={**common_tags, "Name": f"{cluster_name}-igw"},
)

# Create public and private subnets across multiple AZs
public_subnets = []
private_subnets = []

for i, az in enumerate(az_names):
    # Public subnet
    public_subnet = aws.ec2.Subnet(
        f"public-subnet-{i}",
        vpc_id=vpc.id,
        cidr_block=f"10.0.{i}.0/24",
        availability_zone=az,
        map_public_ip_on_launch=True,
        tags={
            **common_tags,
            "Name": f"{cluster_name}-public-{az}",
            "kubernetes.io/role/elb": "1",
            f"kubernetes.io/cluster/{cluster_name}": "shared",
        },
    )
    public_subnets.append(public_subnet)

    # Private subnet
    private_subnet = aws.ec2.Subnet(
        f"private-subnet-{i}",
        vpc_id=vpc.id,
        cidr_block=f"10.0.{i + 10}.0/24",
        availability_zone=az,
        tags={
            **common_tags,
            "Name": f"{cluster_name}-private-{az}",
            "kubernetes.io/role/internal-elb": "1",
            f"kubernetes.io/cluster/{cluster_name}": "shared",
        },
    )
    private_subnets.append(private_subnet)

# Elastic IPs for NAT Gateways
eips = []
for i in range(len(az_names)):
    eip = aws.ec2.Eip(
        f"nat-eip-{i}",
        domain="vpc",
        tags={**common_tags, "Name": f"{cluster_name}-nat-eip-{i}"},
    )
    eips.append(eip)

# NAT Gateways in each public subnet
nat_gateways = []
for i, public_subnet in enumerate(public_subnets):
    nat_gw = aws.ec2.NatGateway(
        f"nat-gateway-{i}",
        allocation_id=eips[i].id,
        subnet_id=public_subnet.id,
        tags={**common_tags, "Name": f"{cluster_name}-nat-{i}"},
    )
    nat_gateways.append(nat_gw)

# Public route table
public_route_table = aws.ec2.RouteTable(
    "public-rt",
    vpc_id=vpc.id,
    tags={**common_tags, "Name": f"{cluster_name}-public-rt"},
)

# Route to Internet Gateway
public_route = aws.ec2.Route(
    "public-route",
    route_table_id=public_route_table.id,
    destination_cidr_block="0.0.0.0/0",
    gateway_id=igw.id,
)

# Associate public subnets with public route table
for i, subnet in enumerate(public_subnets):
    aws.ec2.RouteTableAssociation(
        f"public-rt-assoc-{i}",
        subnet_id=subnet.id,
        route_table_id=public_route_table.id,
    )

# Private route tables (one per AZ for HA)
for i, (subnet, nat_gw) in enumerate(zip(private_subnets, nat_gateways)):
    private_rt = aws.ec2.RouteTable(
        f"private-rt-{i}",
        vpc_id=vpc.id,
        tags={**common_tags, "Name": f"{cluster_name}-private-rt-{i}"},
    )

    aws.ec2.Route(
        f"private-route-{i}",
        route_table_id=private_rt.id,
        destination_cidr_block="0.0.0.0/0",
        nat_gateway_id=nat_gw.id,
    )

    aws.ec2.RouteTableAssociation(
        f"private-rt-assoc-{i}",
        subnet_id=subnet.id,
        route_table_id=private_rt.id,
    )

# ============================================================================
# IAM Roles and Policies
# ============================================================================

# EKS Cluster Role
cluster_role = aws.iam.Role(
    "eks-cluster-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "eks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }""",
    tags={**common_tags, "Name": f"{cluster_name}-cluster-role"},
)

# Attach required policies to cluster role
aws.iam.RolePolicyAttachment(
    "eks-cluster-policy",
    role=cluster_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
)

aws.iam.RolePolicyAttachment(
    "eks-vpc-resource-controller",
    role=cluster_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSVPCResourceController",
)

# Node Group Role
node_role = aws.iam.Role(
    "eks-node-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }""",
    tags={**common_tags, "Name": f"{cluster_name}-node-role"},
)

# Attach required policies to node role
aws.iam.RolePolicyAttachment(
    "eks-worker-node-policy",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
)

aws.iam.RolePolicyAttachment(
    "eks-cni-policy",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
)

aws.iam.RolePolicyAttachment(
    "eks-container-registry-policy",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
)

# Additional policy for SSM access (for debugging)
aws.iam.RolePolicyAttachment(
    "eks-ssm-policy",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
)

# ============================================================================
# Security Groups
# ============================================================================

# EKS Cluster Security Group
cluster_sg = aws.ec2.SecurityGroup(
    "eks-cluster-sg",
    vpc_id=vpc.id,
    description="Security group for EKS cluster control plane",
    tags={**common_tags, "Name": f"{cluster_name}-cluster-sg"},
)

# Allow HTTPS inbound from VPC
aws.ec2.SecurityGroupRule(
    "cluster-ingress-https",
    type="ingress",
    from_port=443,
    to_port=443,
    protocol="tcp",
    cidr_blocks=[vpc_cidr],
    security_group_id=cluster_sg.id,
)

# Node Security Group
node_sg = aws.ec2.SecurityGroup(
    "eks-node-sg",
    vpc_id=vpc.id,
    description="Security group for EKS worker nodes",
    tags={
        **common_tags,
        "Name": f"{cluster_name}-node-sg",
        f"kubernetes.io/cluster/{cluster_name}": "owned",
    },
)

# Allow nodes to communicate with each other
aws.ec2.SecurityGroupRule(
    "node-ingress-self",
    type="ingress",
    from_port=0,
    to_port=65535,
    protocol="-1",
    source_security_group_id=node_sg.id,
    security_group_id=node_sg.id,
)

# Allow pods to communicate with cluster API
aws.ec2.SecurityGroupRule(
    "node-ingress-cluster",
    type="ingress",
    from_port=1025,
    to_port=65535,
    protocol="tcp",
    source_security_group_id=cluster_sg.id,
    security_group_id=node_sg.id,
)

# Allow cluster to communicate with nodes
aws.ec2.SecurityGroupRule(
    "cluster-ingress-node-https",
    type="ingress",
    from_port=443,
    to_port=443,
    protocol="tcp",
    source_security_group_id=node_sg.id,
    security_group_id=cluster_sg.id,
)

# ============================================================================
# EKS Cluster
# ============================================================================

# Create EKS Cluster
eks_cluster = aws.eks.Cluster(
    "eks-cluster",
    name=cluster_name,
    version=cluster_version,
    role_arn=cluster_role.arn,
    vpc_config=aws.eks.ClusterVpcConfigArgs(
        subnet_ids=[subnet.id for subnet in private_subnets + public_subnets],
        security_group_ids=[cluster_sg.id],
        endpoint_private_access=True,
        endpoint_public_access=True,
    ),
    enabled_cluster_log_types=[
        "api",
        "audit",
        "authenticator",
        "controllerManager",
        "scheduler",
    ],
    tags={**common_tags, "Name": cluster_name},
    opts=ResourceOptions(depends_on=[
        cluster_role,
        public_route,
    ])
)

# ============================================================================
# EKS Add-ons
# ============================================================================

# VPC CNI Add-on
vpc_cni_addon = aws.eks.Addon(
    "vpc-cni-addon",
    cluster_name=eks_cluster.name,
    addon_name="vpc-cni",
    addon_version="v1.16.0-eksbuild.1",
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="PRESERVE",
    tags=common_tags,
)

# CoreDNS Add-on
coredns_addon = aws.eks.Addon(
    "coredns-addon",
    cluster_name=eks_cluster.name,
    addon_name="coredns",
    addon_version="v1.11.1-eksbuild.4",
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="PRESERVE",
    tags=common_tags,
    opts=ResourceOptions(depends_on=[vpc_cni_addon])
)

# kube-proxy Add-on
kube_proxy_addon = aws.eks.Addon(
    "kube-proxy-addon",
    cluster_name=eks_cluster.name,
    addon_name="kube-proxy",
    addon_version="v1.29.0-eksbuild.1",
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="PRESERVE",
    tags=common_tags,
)

# EBS CSI Driver Add-on (for persistent volumes)
ebs_csi_role = aws.iam.Role(
    "ebs-csi-driver-role",
    assume_role_policy=eks_cluster.identities[0].oidcs[0].issuer.apply(
        lambda issuer: f"""{{
            "Version": "2012-10-17",
            "Statement": [{{
                "Effect": "Allow",
                "Principal": {{
                    "Federated": "arn:aws:iam::{aws.get_caller_identity().account_id}:oidc-provider/{issuer.replace('https://', '')}"
                }},
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {{
                    "StringEquals": {{
                        "{issuer.replace('https://', '')}:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa",
                        "{issuer.replace('https://', '')}:aud": "sts.amazonaws.com"
                    }}
                }}
            }}]
        }}"""
    ),
    tags={**common_tags, "Name": f"{cluster_name}-ebs-csi-role"},
)

aws.iam.RolePolicyAttachment(
    "ebs-csi-policy",
    role=ebs_csi_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy",
)

ebs_csi_addon = aws.eks.Addon(
    "ebs-csi-addon",
    cluster_name=eks_cluster.name,
    addon_name="aws-ebs-csi-driver",
    addon_version="v1.27.0-eksbuild.1",
    service_account_role_arn=ebs_csi_role.arn,
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="PRESERVE",
    tags=common_tags,
)

# ============================================================================
# Node Group
# ============================================================================

# Create Managed Node Group
node_group = aws.eks.NodeGroup(
    "eks-node-group",
    cluster_name=eks_cluster.name,
    node_group_name=f"{cluster_name}-node-group",
    node_role_arn=node_role.arn,
    subnet_ids=[subnet.id for subnet in private_subnets],
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=desired_capacity,
        max_size=max_size,
        min_size=min_size,
    ),
    instance_types=[instance_type],
    ami_type="AL2_x86_64",
    capacity_type="ON_DEMAND",
    disk_size=50,
    update_config=aws.eks.NodeGroupUpdateConfigArgs(
        max_unavailable=1,
    ),
    labels={
        "role": "general",
        "environment": pulumi.get_stack(),
    },
    tags={
        **common_tags,
        "Name": f"{cluster_name}-node-group",
    },
    opts=ResourceOptions(depends_on=[
        node_role,
        eks_cluster,
        vpc_cni_addon,
        coredns_addon,
        kube_proxy_addon,
    ])
)

# ============================================================================
# OIDC Provider for IRSA (IAM Roles for Service Accounts)
# ============================================================================

# Get the OIDC provider thumbprint
oidc_thumbprint = "9e99a48a9960b14926bb7f3b02e22da2b0ab7280"  # AWS OIDC thumbprint

oidc_provider = aws.iam.OpenIdConnectProvider(
    "eks-oidc-provider",
    client_id_lists=["sts.amazonaws.com"],
    thumbprint_lists=[oidc_thumbprint],
    url=eks_cluster.identities[0].oidcs[0].issuer,
    tags={**common_tags, "Name": f"{cluster_name}-oidc-provider"},
)

# ============================================================================
# Generate kubeconfig
# ============================================================================

def generate_kubeconfig(cluster_name, cluster_endpoint, cluster_ca):
    return f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {cluster_ca}
    server: {cluster_endpoint}
  name: {cluster_name}
contexts:
- context:
    cluster: {cluster_name}
    user: {cluster_name}
  name: {cluster_name}
current-context: {cluster_name}
kind: Config
preferences: {{}}
users:
- name: {cluster_name}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: aws
      args:
        - eks
        - get-token
        - --cluster-name
        - {cluster_name}
        - --output
        - json
"""

kubeconfig = Output.all(
    eks_cluster.name,
    eks_cluster.endpoint,
    eks_cluster.certificate_authority.data
).apply(lambda args: generate_kubeconfig(args[0], args[1], args[2]))

# ============================================================================
# Exports
# ============================================================================

pulumi.export("cluster_name", eks_cluster.name)
pulumi.export("cluster_endpoint", eks_cluster.endpoint)
pulumi.export("cluster_security_group_id", cluster_sg.id)
pulumi.export("node_security_group_id", node_sg.id)
pulumi.export("cluster_arn", eks_cluster.arn)
pulumi.export("cluster_version", eks_cluster.version)
pulumi.export("vpc_id", vpc.id)
pulumi.export("private_subnet_ids", [subnet.id for subnet in private_subnets])
pulumi.export("public_subnet_ids", [subnet.id for subnet in public_subnets])
pulumi.export("node_role_arn", node_role.arn)
pulumi.export("oidc_provider_arn", oidc_provider.arn)
pulumi.export("oidc_provider_url", oidc_provider.url)
pulumi.export("kubeconfig", kubeconfig)

# Export a command to update local kubeconfig
pulumi.export(
    "update_kubeconfig_command",
    Output.concat(
        "aws eks update-kubeconfig --region ",
        aws.config.region,
        " --name ",
        eks_cluster.name
    )
)

print("\n✅ EKS cluster infrastructure created successfully!")
print(f"📋 Cluster name: {cluster_name}")
print(f"🌐 Region: {aws.config.region}")
print(f"📦 Kubernetes version: {cluster_version}")
