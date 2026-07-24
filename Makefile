.PHONY: help install init preview up destroy refresh config clean kubeconfig

# Default target
help:
	@echo "Pulumi EKS Cluster Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make install       - Create virtual environment and install dependencies"
	@echo "  make init          - Initialize a new Pulumi stack"
	@echo "  make config        - Show current configuration"
	@echo "  make preview       - Preview infrastructure changes"
	@echo "  make up            - Deploy infrastructure"
	@echo "  make refresh       - Refresh stack state"
	@echo "  make destroy       - Destroy all infrastructure"
	@echo "  make kubeconfig    - Update local kubeconfig for the cluster"
	@echo "  make clean         - Remove virtual environment"
	@echo ""

# Install dependencies
install:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Installing dependencies..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Installation complete!"
	@echo "Run 'source venv/bin/activate' to activate the virtual environment"

# Initialize Pulumi stack
init:
	@echo "Initializing Pulumi stack..."
	@read -p "Enter stack name (e.g., dev, staging, prod): " stack; \
	pulumi stack init $$stack
	@read -p "Enter AWS region (e.g., us-east-1): " region; \
	pulumi config set aws:region $$region
	@read -p "Enter cluster name: " name; \
	pulumi config set pulumi-eks-cluster:clusterName $$name
	@echo "✅ Stack initialized! Run 'make config' to review settings."

# Show configuration
config:
	@echo "Current Pulumi configuration:"
	@pulumi config
	@echo ""
	@echo "Current stack:"
	@pulumi stack --show-name

# Preview changes
preview:
	@echo "Previewing infrastructure changes..."
	pulumi preview

# Deploy infrastructure
up:
	@echo "Deploying infrastructure..."
	@echo "⚠️  This will take approximately 15-20 minutes"
	pulumi up

# Refresh stack state
refresh:
	@echo "Refreshing stack state..."
	pulumi refresh

# Destroy infrastructure
destroy:
	@echo "⚠️  WARNING: This will destroy all infrastructure!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		pulumi destroy; \
	else \
		echo "Cancelled."; \
	fi

# Update kubeconfig
kubeconfig:
	@echo "Updating kubeconfig..."
	@CLUSTER_NAME=$$(pulumi stack output cluster_name 2>/dev/null); \
	if [ -z "$$CLUSTER_NAME" ]; then \
		echo "❌ Cluster not found. Make sure the stack is deployed."; \
		exit 1; \
	fi; \
	REGION=$$(pulumi config get aws:region); \
	aws eks update-kubeconfig --region $$REGION --name $$CLUSTER_NAME
	@echo "✅ kubeconfig updated!"
	@echo ""
	@echo "Verifying connection..."
	kubectl get nodes

# Clean virtual environment
clean:
	@echo "Removing virtual environment..."
	rm -rf venv
	@echo "✅ Clean complete!"

# Quick setup for new users
setup: install init
	@echo "✅ Setup complete! Next steps:"
	@echo "1. Activate virtual environment: source venv/bin/activate"
	@echo "2. Review configuration: make config"
	@echo "3. Preview changes: make preview"
	@echo "4. Deploy: make up"
