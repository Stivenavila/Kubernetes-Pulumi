# 🚀 Quick Start Guide - EKS Cluster Deployment

This guide will get your production-ready EKS cluster up and running in under 30 minutes.

## 📋 Prerequisites Checklist

- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Python 3.8+ installed
- [ ] Pulumi CLI installed
- [ ] kubectl installed
- [ ] Sufficient AWS permissions (VPC, EKS, IAM, EC2)
- [ ] Optional: Helm installed for add-ons

## ⚡ Fast Track Deployment

### Step 1: Setup Project

```bash
cd /path/to/pulumi-eks-cluster

# Quick setup with Makefile
make setup

# Or manual setup:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pulumi login
pulumi stack init dev
pulumi config set aws:region us-east-1
pulumi config set pulumi-eks-cluster:clusterName my-eks-cluster
```

### Step 2: Review Configuration

```bash
make config
# or
pulumi config
```

### Step 3: Preview and Deploy

```bash
make preview
make up   # ~15-20 minutes
```

### Step 4: Configure kubectl

```bash
make kubeconfig
# or
aws eks update-kubeconfig --region us-east-1 --name my-eks-cluster

kubectl get nodes
kubectl get pods -A
```

### Step 5: Deploy Test Application

```bash
kubectl apply -f k8s-examples/nginx-deployment.yaml
kubectl get pods -n demo -w
kubectl get svc -n demo nginx-service
```

## 🔧 Post-Deployment Setup

### Metrics Server (for HPA)

```bash
chmod +x scripts/install-metrics-server.sh
./scripts/install-metrics-server.sh
kubectl top nodes
```

### AWS Load Balancer Controller (for Ingress)

```bash
chmod +x scripts/install-aws-lb-controller.sh
./scripts/install-aws-lb-controller.sh
kubectl get deployment -n kube-system aws-load-balancer-controller
```

## 🗑️ Cleanup

```bash
kubectl delete -f k8s-examples/nginx-deployment.yaml
make destroy   # type 'yes' to confirm
```

## ❓ Troubleshooting

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Update kubeconfig
aws eks update-kubeconfig --region <region> --name <cluster-name>

# Check node group status
aws eks describe-nodegroup --cluster-name <name> --nodegroup-name <name>

# Inspect pods
kubectl describe pod <pod-name> -n <namespace>
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

---

**Contact**: Stiven Avila M. — stivenavilam@gmail.com
