#!/bin/bash
set -e

# Script to install AWS Load Balancer Controller
# This enables Ingress resources to create Application Load Balancers

echo "🚀 Installing AWS Load Balancer Controller..."

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo "❌ helm is not installed"
    echo "Install from: https://helm.sh/docs/intro/install/"
    exit 1
fi

# Get cluster name from Pulumi or user input
if command -v pulumi &> /dev/null; then
    CLUSTER_NAME=$(pulumi stack output cluster_name 2>/dev/null || echo "")
    AWS_REGION=$(pulumi config get aws:region 2>/dev/null || echo "")
else
    CLUSTER_NAME=""
    AWS_REGION=""
fi

if [ -z "$CLUSTER_NAME" ]; then
    read -p "Enter EKS cluster name: " CLUSTER_NAME
fi

if [ -z "$AWS_REGION" ]; then
    read -p "Enter AWS region: " AWS_REGION
fi

echo "Cluster: $CLUSTER_NAME"
echo "Region: $AWS_REGION"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account: $AWS_ACCOUNT_ID"

# Create IAM policy for Load Balancer Controller
echo "📝 Creating IAM policy..."
POLICY_NAME="AWSLoadBalancerControllerIAMPolicy"

curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.0/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file://iam_policy.json \
    2>/dev/null || echo "Policy already exists"

rm iam_policy.json

# Get OIDC provider ID
OIDC_PROVIDER=$(aws eks describe-cluster --name $CLUSTER_NAME --region $AWS_REGION --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")
OIDC_ID=$(echo $OIDC_PROVIDER | awk -F'/' '{print $NF}')

# Create IAM role for service account
echo "🔐 Creating IAM role for service account..."
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:aud": "sts.amazonaws.com",
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:kube-system:aws-load-balancer-controller"
        }
      }
    }
  ]
}
EOF

ROLE_NAME="AmazonEKSLoadBalancerControllerRole"

aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://trust-policy.json \
    --description "Role for AWS Load Balancer Controller" \
    2>/dev/null || echo "Role already exists"

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}

rm trust-policy.json

# Install AWS Load Balancer Controller using Helm
echo "📦 Installing AWS Load Balancer Controller via Helm..."
helm repo add eks https://aws.github.io/eks-charts
helm repo update

kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller/crds?ref=master"

VPC_ID=$(pulumi stack output vpc_id 2>/dev/null || aws eks describe-cluster --name $CLUSTER_NAME --region $AWS_REGION --query "cluster.resourcesVpcConfig.vpcId" --output text)

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName=$CLUSTER_NAME \
    --set serviceAccount.create=true \
    --set serviceAccount.name=aws-load-balancer-controller \
    --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}" \
    --set region=$AWS_REGION \
    --set vpcId=$VPC_ID

echo ""
echo "✅ AWS Load Balancer Controller installed successfully!"
echo ""
echo "Verify installation:"
echo "  kubectl get deployment -n kube-system aws-load-balancer-controller"
echo "  kubectl logs -n kube-system deployment/aws-load-balancer-controller"
