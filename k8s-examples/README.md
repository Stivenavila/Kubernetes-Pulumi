# Kubernetes Example Deployments

This directory contains example Kubernetes manifests to test your EKS cluster.

## Prerequisites

```bash
# Update kubeconfig
aws eks update-kubeconfig --region <region> --name <cluster-name>
# or
make kubeconfig
```

## Nginx Demo Application

A simple nginx deployment with LoadBalancer service and HPA.

### Deploy

```bash
kubectl apply -f nginx-deployment.yaml
```

### Verify

```bash
kubectl get namespace demo
kubectl get deployment -n demo
kubectl get pods -n demo
kubectl get svc nginx-service -n demo -w
kubectl get hpa -n demo
```

### Access the Application

```bash
export LB_URL=$(kubectl get svc nginx-service -n demo -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Application URL: http://$LB_URL"
curl http://$LB_URL
```

### Scale Test

```bash
kubectl run -it --rm load-generator --image=busybox -n demo -- /bin/sh
# Inside the pod:
while true; do wget -q -O- http://nginx-service.demo.svc.cluster.local; done

# Watch HPA in another terminal
kubectl get hpa -n demo -w
```

### Cleanup

```bash
kubectl delete -f nginx-deployment.yaml
```

## Useful Commands

```bash
kubectl get all -n demo
kubectl logs -n demo -l app=nginx
kubectl exec -it -n demo <pod-name> -- /bin/sh
kubectl port-forward -n demo svc/nginx-service 8080:80
kubectl top nodes
kubectl top pods -n demo
```
