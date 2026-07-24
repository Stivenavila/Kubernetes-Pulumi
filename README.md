# AWS EKS Cluster with Pulumi

Production-ready Amazon Elastic Kubernetes Service (EKS) cluster deployed using Pulumi Infrastructure as Code.

## 🏗️ Architecture Overview

This project deploys a complete, production-ready Kubernetes environment on AWS with:

### Network Infrastructure
- **VPC** with custom CIDR block (default: 10.0.0.0/16)
- **Multi-AZ deployment** across 3 Availability Zones for high availability
- **Public subnets** (3) for load balancers and bastion hosts
- **Private subnets** (3) for EKS worker nodes
- **NAT Gateways** in each AZ for outbound internet access from private subnets
- **Internet Gateway** for public subnet access
- **Route tables** properly configured for public and private traffic

### EKS Cluster
- **Managed EKS control plane** (configurable Kubernetes version)
- **Managed node groups** with auto-scaling capabilities
- **OIDC provider** for IAM Roles for Service Accounts (IRSA)
- **EKS Add-ons**:
  - VPC CNI (for pod networking)
  - CoreDNS (for service discovery)
  - kube-proxy (for service routing)
  - EBS CSI Driver (for persistent volumes)
- **CloudWatch logging** enabled for all control plane components

### Security
- **IAM roles** with least-privilege access for cluster and nodes
- **Security groups** with minimal required ingress/egress rules
- **Private API endpoint** support (with optional public access)
- **SSM access** enabled on nodes for secure debugging
- **Network isolation** with nodes in private subnets

## 📋 Prerequisites

### Required Tools
- [Pulumi](https://www.pulumi.com/docs/get-started/install/) >= 3.100.0
- [Python](https://www.python.org/downloads/) >= 3.8
- [AWS CLI](https://aws.amazon.com/cli/) v2
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

### AWS Configuration
1. **AWS Credentials**: Ensure you have valid AWS credentials configured
   ```bash
   aws configure
   ```

2. **Required IAM Permissions**: Your IAM user/role needs permissions to create:
   - VPC, Subnets, Route Tables, Internet Gateways, NAT Gateways
   - EKS Clusters and Node Groups
   - IAM Roles and Policies
   - EC2 Security Groups
   - CloudWatch Log Groups

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Navigate to the project directory
cd pulumi-eks-cluster

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Your Stack

```bash
# Login to Pulumi (use local backend or Pulumi Cloud)
pulumi login

# Create a new stack (e.g., dev, staging, prod)
pulumi stack init dev

# Set AWS region
pulumi config set aws:region us-east-1

# Optional: Customize cluster settings
pulumi config set pulumi-eks-cluster:clusterName my-eks-cluster
pulumi config set pulumi-eks-cluster:clusterVersion 1.29
pulumi config set pulumi-eks-cluster:instanceType t3.large
pulumi config set pulumi-eks-cluster:desiredCapacity 3
pulumi config set pulumi-eks-cluster:minSize 2
pulumi config set pulumi-eks-cluster:maxSize 6
```

### 3. Preview and Deploy

```bash
# Preview the changes
pulumi preview

# Deploy the infrastructure
pulumi up

# The deployment will take approximately 15-20 minutes
```

### 4. Configure kubectl

After deployment completes, configure kubectl to access your cluster:

```bash
# Option 1: Use AWS CLI
aws eks update-kubeconfig --region us-east-1 --name <cluster-name>

# Option 2: Use kubeconfig from Pulumi output
pulumi stack output kubeconfig > kubeconfig.yaml
export KUBECONFIG=./kubeconfig.yaml

# Verify connection
kubectl get nodes
kubectl get pods -A
```

## ⚙️ Configuration Options

| Parameter | Description | Default | Type |
|-----------|-------------|---------|------|
| `aws:region` | AWS region for deployment | `us-east-1` | string |
| `clusterName` | Name of the EKS cluster | `eks-cluster` | string |
| `clusterVersion` | Kubernetes version | `1.29` | string |
| `desiredCapacity` | Desired number of nodes | `2` | int |
| `minSize` | Minimum number of nodes | `1` | int |
| `maxSize` | Maximum number of nodes | `4` | int |
| `instanceType` | EC2 instance type for nodes | `t3.medium` | string |
| `vpcCidr` | CIDR block for VPC | `10.0.0.0/16` | string |

### Setting Configuration

```bash
# Set a configuration value
pulumi config set <key> <value>

# Set a secret value (encrypted)
pulumi config set --secret <key> <value>

# View current configuration
pulumi config

# View all outputs
pulumi stack output
```

## 📤 Stack Outputs

After deployment, the following outputs are available:

| Output | Description |
|--------|-------------|
| `cluster_name` | Name of the EKS cluster |
| `cluster_endpoint` | Kubernetes API endpoint |
| `cluster_arn` | ARN of the EKS cluster |
| `cluster_version` | Kubernetes version |
| `vpc_id` | VPC ID |
| `private_subnet_ids` | List of private subnet IDs |
| `public_subnet_ids` | List of public subnet IDs |
| `cluster_security_group_id` | Security group ID for cluster |
| `node_security_group_id` | Security group ID for nodes |
| `node_role_arn` | IAM role ARN for nodes |
| `oidc_provider_arn` | OIDC provider ARN for IRSA |
| `oidc_provider_url` | OIDC provider URL |
| `kubeconfig` | Complete kubeconfig file content |
| `update_kubeconfig_command` | AWS CLI command to update kubeconfig |

### Accessing Outputs

```bash
# View all outputs
pulumi stack output

# Get a specific output
pulumi stack output cluster_endpoint

# Get kubeconfig
pulumi stack output kubeconfig

# Get and run the update-kubeconfig command
pulumi stack output update_kubeconfig_command
```

## 🔧 Common Operations

### Scaling the Node Group

```bash
# Update desired capacity
pulumi config set pulumi-eks-cluster:desiredCapacity 5
pulumi up

# Update min/max sizes
pulumi config set pulumi-eks-cluster:minSize 3
pulumi config set pulumi-eks-cluster:maxSize 10
pulumi up
```

### Upgrading Kubernetes Version

```bash
# Update to a new version (check AWS EKS supported versions)
pulumi config set pulumi-eks-cluster:clusterVersion 1.30
pulumi up

# Note: This will trigger a rolling update of your node group
```

### Changing Instance Type

```bash
pulumi config set pulumi-eks-cluster:instanceType t3.large
pulumi up

# This will create a new node group and drain the old one
```

## 🔐 IAM Roles for Service Accounts (IRSA)

The cluster includes an OIDC provider for IRSA. Use the `oidc_provider_arn` and
`oidc_provider_url` outputs to create IAM roles that pods can assume via their
Kubernetes service accounts, following the principle of least privilege.

## 📊 Monitoring and Logging

### CloudWatch Logs

Control plane logs are automatically sent to CloudWatch Logs:

```bash
# Get log group name
aws logs describe-log-groups --log-group-name-prefix /aws/eks/<cluster-name>

# Stream logs (example for API server)
aws logs tail /aws/eks/<cluster-name>/cluster --follow
```

### Metrics Server

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl top nodes
kubectl top pods -A
```

## 🧹 Cleanup

```bash
# Preview what will be destroyed
pulumi destroy --preview

# Destroy all resources
pulumi destroy

# Remove the stack
pulumi stack rm dev
```

**Important**: Delete any load balancers or persistent volumes created by
Kubernetes before running `pulumi destroy`, as they may prevent the VPC from
being deleted.

## 🏢 Production Considerations

- Multi-AZ deployment with NAT Gateway per AZ for high availability
- Nodes in private subnets with least-privilege IAM roles
- Consider Spot instances and Cluster Autoscaler / Karpenter for cost savings
- Implement Network Policies, Pod Security Standards, and secrets encryption
- Use Velero for backups and enable VPC Flow Logs for network monitoring

## 📚 Additional Resources

- [AWS EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [Pulumi AWS Documentation](https://www.pulumi.com/registry/packages/aws/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

**Created by**: Stiven Avila M.
**Specialization**: AWS Cloud Architecture, Kubernetes, DevOps, Security
**Contact**: stivenavilam@gmail.com
