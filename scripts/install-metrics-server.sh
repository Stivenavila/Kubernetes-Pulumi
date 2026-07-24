#!/bin/bash
set -e

echo "📊 Installing Kubernetes Metrics Server..."

if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    exit 1
fi

kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

echo ""
echo "⏳ Waiting for Metrics Server to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/metrics-server -n kube-system

echo ""
echo "✅ Metrics Server installed successfully!"
echo ""
echo "View metrics:"
echo "  kubectl top nodes"
echo "  kubectl top pods -A"
