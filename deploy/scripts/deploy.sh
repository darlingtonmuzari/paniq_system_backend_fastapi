#!/bin/bash

# Panic System Platform Deployment Script
# Usage: ./deploy.sh [environment] [version]
# Example: ./deploy.sh production v1.2.3

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENVIRONMENTS_DIR="$PROJECT_ROOT/deploy/environments"
K8S_DIR="$PROJECT_ROOT/k8s"

# Default values
ENVIRONMENT="${1:-staging}"
VERSION="${2:-latest}"
NAMESPACE="panic-system"
REGISTRY="ghcr.io/panicsystem/panic-system-platform"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validation functions
validate_environment() {
    if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        log_info "Valid environments: development, staging, production"
        exit 1
    fi
}

validate_version() {
    if [[ "$VERSION" != "latest" && ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format: $VERSION"
        log_info "Version should be 'latest' or follow semantic versioning (e.g., v1.2.3)"
        exit 1
    fi
}

validate_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
}

validate_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    validate_environment
    validate_version
    validate_kubectl
    validate_docker
    
    # Check if namespace exists
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        NAMESPACE="panic-system-staging"
    fi
    
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE does not exist, creating it..."
        kubectl create namespace "$NAMESPACE"
    fi
    
    # Check if required secrets exist
    if ! kubectl get secret panic-system-secrets -n "$NAMESPACE" &> /dev/null; then
        log_error "Required secret 'panic-system-secrets' not found in namespace $NAMESPACE"
        log_info "Please create the secret before deploying"
        exit 1
    fi
    
    log_success "Pre-deployment checks passed"
}

# Build and push Docker image
build_and_push_image() {
    if [[ "$VERSION" == "latest" ]]; then
        log_info "Skipping image build for 'latest' version"
        return
    fi
    
    log_info "Building Docker image for version $VERSION..."
    
    cd "$PROJECT_ROOT"
    
    # Build image
    docker build -t "$REGISTRY:$VERSION" --target production .
    
    # Push image
    log_info "Pushing image to registry..."
    docker push "$REGISTRY:$VERSION"
    
    log_success "Image built and pushed: $REGISTRY:$VERSION"
}

# Update Kubernetes manifests
update_manifests() {
    log_info "Updating Kubernetes manifests..."
    
    # Create temporary directory for modified manifests
    TEMP_DIR=$(mktemp -d)
    cp -r "$K8S_DIR"/* "$TEMP_DIR/"
    
    # Update image tag in deployment
    IMAGE_TAG="$REGISTRY:$VERSION"
    sed -i "s|panic-system-api:latest|$IMAGE_TAG|g" "$TEMP_DIR/api-deployment.yaml"
    
    # Update namespace in manifests if staging
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        find "$TEMP_DIR" -name "*.yaml" -exec sed -i "s/namespace: panic-system$/namespace: panic-system-staging/g" {} \;
    fi
    
    echo "$TEMP_DIR"
}

# Deploy infrastructure components
deploy_infrastructure() {
    local temp_dir="$1"
    
    log_info "Deploying infrastructure components..."
    
    # Apply namespace
    kubectl apply -f "$temp_dir/namespace.yaml"
    
    # Apply ConfigMap
    kubectl apply -f "$temp_dir/configmap.yaml"
    
    # Apply secrets (only if they don't exist)
    if ! kubectl get secret panic-system-secrets -n "$NAMESPACE" &> /dev/null; then
        kubectl apply -f "$temp_dir/secrets.yaml"
    fi
    
    # Deploy PostgreSQL
    kubectl apply -f "$temp_dir/postgres.yaml"
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n "$NAMESPACE" --timeout=300s
    
    # Deploy Redis
    kubectl apply -f "$temp_dir/redis.yaml"
    log_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
    
    log_success "Infrastructure components deployed"
}

# Deploy application
deploy_application() {
    local temp_dir="$1"
    
    log_info "Deploying application..."
    
    # Apply API deployment
    kubectl apply -f "$temp_dir/api-deployment.yaml"
    
    # Wait for deployment to complete
    log_info "Waiting for application deployment to complete..."
    kubectl rollout status deployment/panic-system-api -n "$NAMESPACE" --timeout=600s
    
    # Apply ingress
    kubectl apply -f "$temp_dir/ingress.yaml"
    
    log_success "Application deployed"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Create migration job
    JOB_NAME="db-migration-$(date +%s)"
    kubectl create job --from=deployment/panic-system-api "$JOB_NAME" -n "$NAMESPACE"
    
    # Override command to run migrations
    kubectl patch job "$JOB_NAME" -n "$NAMESPACE" --type='merge' -p='{
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "api",
                        "command": ["python", "-m", "alembic", "upgrade", "head"]
                    }]
                }
            }
        }
    }'
    
    # Wait for migration to complete
    kubectl wait --for=condition=complete job/"$JOB_NAME" -n "$NAMESPACE" --timeout=300s
    
    # Clean up migration job
    kubectl delete job "$JOB_NAME" -n "$NAMESPACE"
    
    log_success "Database migrations completed"
}

# Post-deployment verification
post_deployment_verification() {
    log_info "Running post-deployment verification..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app=panic-system-api -n "$NAMESPACE" --timeout=300s
    
    # Get service endpoint
    if [[ "$ENVIRONMENT" == "production" ]]; then
        ENDPOINT="https://api.panicsystem.com"
    elif [[ "$ENVIRONMENT" == "staging" ]]; then
        ENDPOINT="https://staging-api.panicsystem.com"
    else
        ENDPOINT="http://localhost:8000"
    fi
    
    # Health check
    log_info "Performing health check..."
    for i in {1..10}; do
        if curl -f "$ENDPOINT/health" &> /dev/null; then
            log_success "Health check passed"
            break
        fi
        if [[ $i -eq 10 ]]; then
            log_error "Health check failed after 10 attempts"
            exit 1
        fi
        log_info "Health check attempt $i failed, retrying in 10 seconds..."
        sleep 10
    done
    
    # API version check
    log_info "Checking API version..."
    API_RESPONSE=$(curl -s "$ENDPOINT/api/v1/" | jq -r '.message' 2>/dev/null || echo "")
    if [[ "$API_RESPONSE" == "Panic System Platform API v1" ]]; then
        log_success "API version check passed"
    else
        log_warning "API version check returned unexpected response: $API_RESPONSE"
    fi
    
    log_success "Post-deployment verification completed"
}

# Rollback function
rollback_deployment() {
    log_warning "Rolling back deployment..."
    
    # Rollback API deployment
    kubectl rollout undo deployment/panic-system-api -n "$NAMESPACE"
    kubectl rollout status deployment/panic-system-api -n "$NAMESPACE" --timeout=300s
    
    log_success "Rollback completed"
}

# Cleanup function
cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}

# Main deployment function
main() {
    log_info "Starting deployment of Panic System Platform"
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    log_info "Namespace: $NAMESPACE"
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Run deployment steps
    pre_deployment_checks
    
    if [[ "$ENVIRONMENT" != "development" ]]; then
        build_and_push_image
    fi
    
    TEMP_DIR=$(update_manifests)
    
    deploy_infrastructure "$TEMP_DIR"
    run_migrations
    deploy_application "$TEMP_DIR"
    post_deployment_verification
    
    log_success "Deployment completed successfully!"
    log_info "Application is available at:"
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_info "  Production: https://api.panicsystem.com"
    elif [[ "$ENVIRONMENT" == "staging" ]]; then
        log_info "  Staging: https://staging-api.panicsystem.com"
    else
        log_info "  Development: http://localhost:8000"
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Panic System Platform Deployment Script"
        echo ""
        echo "Usage: $0 [environment] [version]"
        echo ""
        echo "Arguments:"
        echo "  environment    Target environment (development|staging|production)"
        echo "  version        Application version (latest|v1.2.3)"
        echo ""
        echo "Examples:"
        echo "  $0 staging latest"
        echo "  $0 production v1.2.3"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --rollback     Rollback the last deployment"
        exit 0
        ;;
    --rollback)
        ENVIRONMENT="${2:-staging}"
        validate_environment
        if [[ "$ENVIRONMENT" == "staging" ]]; then
            NAMESPACE="panic-system-staging"
        fi
        rollback_deployment
        exit 0
        ;;
    *)
        main
        ;;
esac