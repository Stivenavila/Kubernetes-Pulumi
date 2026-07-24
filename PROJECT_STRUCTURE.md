# Project Structure

```
pulumi-eks-cluster/
│
├── __main__.py                 # Main Pulumi program (Infrastructure as Code)
│   ├── VPC and Networking (Multi-AZ)
│   ├── EKS Cluster Configuration
│   ├── Managed Node Groups
│   ├── IAM Roles and Policies
│   ├── Security Groups
│   ├── EKS Add-ons (CNI, CoreDNS, kube-proxy, EBS CSI)
│   └── OIDC Provider for IRSA
│
├── requirements.txt            # Python dependencies
├── Pulumi.yaml                 # Pulumi project configuration
├── Pulumi.dev.yaml             # Example stack configuration (dev)
├── .gitignore                  # Git ignore patterns
├── Makefile                    # Convenience commands
│
├── README.md                   # Complete documentation
├── QUICKSTART.md               # Fast-track deployment guide
├── PROJECT_STRUCTURE.md        # This file
│
├── k8s-examples/               # Kubernetes example manifests
│   ├── nginx-deployment.yaml   # Sample app (Deployment + Service + HPA)
│   └── README.md               # Instructions for examples
│
└── scripts/                    # Helper scripts
    ├── install-aws-lb-controller.sh    # Install ALB Controller
    └── install-metrics-server.sh       # Install Metrics Server
```

## Resource Count

| Resource Type | Count | Notes |
|---------------|-------|-------|
| VPC | 1 | 10.0.0.0/16 CIDR |
| Subnets | 6 | 3 public + 3 private across 3 AZs |
| NAT Gateways | 3 | One per AZ for HA |
| Internet Gateway | 1 | For public subnets |
| Route Tables | 4 | 1 public + 3 private |
| Security Groups | 2 | Cluster + Node |
| IAM Roles | 3 | Cluster + Node + EBS CSI |
| EKS Cluster | 1 | Managed control plane |
| Node Group | 1 | Managed, auto-scaling |
| Elastic IPs | 3 | For NAT Gateways |
| OIDC Provider | 1 | For IRSA |

**Total**: ~45-50 resources

## Estimated Monthly Cost (us-east-1)

| Component | Cost |
|-----------|------|
| EKS Control Plane | ~$73 |
| EC2 Instances (2x t3.medium) | ~$60 |
| NAT Gateways (3x) | ~$97 |
| NAT Gateway Data | ~$45 |
| EBS Volumes | ~$10 |

**Estimated Total**: ~$285-350/month

Cost optimization: use 1 NAT Gateway (save ~$65/mo), Spot instances (save up to 70%),
smaller instances for dev, and a cluster autoscaler to scale down when idle.

## Deployment Timeline

| Phase | Time |
|-------|------|
| Setup | 5 min |
| VPC & Networking | 3-5 min |
| IAM Resources | 1-2 min |
| EKS Control Plane | 10-12 min |
| Node Group | 3-5 min |
| Add-ons | 2-3 min |

**Total**: ~20-30 minutes end-to-end

---

Created by: Stiven Avila M. — AWS Cloud Architect | Kubernetes Specialist
Email: stivenavilam@gmail.com
