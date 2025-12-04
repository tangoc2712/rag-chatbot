#!/bin/bash

# RAG Service - Cloud Run Deployment Script
# This script deploys the RAG service to Google Cloud Run

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-asia-southeast1}"
SERVICE_NAME="rag-service"
MEMORY="${MEMORY:-2Gi}"
CPU="${CPU:-2}"
MAX_INSTANCES="${MAX_INSTANCES:-10}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
TIMEOUT="${TIMEOUT:-300}"

# Database configuration (from environment or prompt)
DB_HOST="${DB_HOST:-}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ecommerce_rag}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD_SECRET="${DB_PASSWORD_SECRET:-}"
GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --authenticated)
            AUTHENTICATED="true"
            shift
            ;;
        --help)
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --project PROJECT_ID      GCP Project ID"
            echo "  --region REGION          GCP Region (default: asia-southeast1)"
            echo "  --authenticated          Require authentication (default: allow unauthenticated)"
            echo "  --help                   Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  GCP_PROJECT_ID          GCP Project ID"
            echo "  GCP_REGION              GCP Region"
            echo "  DB_HOST                 Database host (Cloud SQL instance connection name)"
            echo "  DB_PORT                 Database port (default: 5432)"
            echo "  DB_NAME                 Database name (default: ecommerce_rag)"
            echo "  DB_USER                 Database user (default: postgres)"
            echo "  DB_PASSWORD_SECRET      Secret Manager secret name for DB password"
            echo "  GOOGLE_API_KEY          Google API key for Gemini"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$PROJECT_ID" ]; then
    print_error "Project ID is required. Set GCP_PROJECT_ID or use --project"
    exit 1
fi

if [ -z "$DB_HOST" ]; then
    print_warning "DB_HOST not set. You'll need to configure it later."
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    print_warning "GOOGLE_API_KEY not set. The service may not work without it."
fi

print_info "Starting deployment to Cloud Run..."
print_info "Project: $PROJECT_ID"
print_info "Region: $REGION"
print_info "Service: $SERVICE_NAME"

# Set the project
print_info "Setting GCP project..."
gcloud config set project "$PROJECT_ID"

# Enable required APIs
print_info "Enabling required Google Cloud APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    --quiet

# Build the container image
print_info "Building container image..."
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
gcloud builds submit --tag "$IMAGE_NAME" .

# Prepare deployment command
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --port 8000 \
    --memory $MEMORY \
    --cpu $CPU \
    --timeout $TIMEOUT \
    --max-instances $MAX_INSTANCES \
    --min-instances $MIN_INSTANCES"

# Add environment variables
ENV_VARS="PORT=8000"
[ -n "$DB_HOST" ] && ENV_VARS="$ENV_VARS,DB_HOST=$DB_HOST"
[ -n "$DB_PORT" ] && ENV_VARS="$ENV_VARS,DB_PORT=$DB_PORT"
[ -n "$DB_NAME" ] && ENV_VARS="$ENV_VARS,DB_NAME=$DB_NAME"
[ -n "$DB_USER" ] && ENV_VARS="$ENV_VARS,DB_USER=$DB_USER"
[ -n "$GOOGLE_API_KEY" ] && ENV_VARS="$ENV_VARS,GOOGLE_API_KEY=$GOOGLE_API_KEY"

DEPLOY_CMD="$DEPLOY_CMD --set-env-vars $ENV_VARS"

# Add secrets if configured
if [ -n "$DB_PASSWORD_SECRET" ]; then
    print_info "Configuring database password from Secret Manager..."
    DEPLOY_CMD="$DEPLOY_CMD --set-secrets DB_PASSWORD=$DB_PASSWORD_SECRET:latest"
fi

# Add authentication settings
if [ "$AUTHENTICATED" = "true" ]; then
    print_info "Deploying with authentication required..."
    DEPLOY_CMD="$DEPLOY_CMD --no-allow-unauthenticated"
else
    print_info "Deploying with public access (no authentication)..."
    DEPLOY_CMD="$DEPLOY_CMD --allow-unauthenticated"
fi

# Deploy to Cloud Run
print_info "Deploying to Cloud Run..."
eval $DEPLOY_CMD

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --format='value(status.url)')

print_info "=========================================="
print_info "Deployment completed successfully!"
print_info "=========================================="
print_info "Service URL: $SERVICE_URL"
print_info ""
print_info "Test the service:"
print_info "  curl $SERVICE_URL/health"
print_info ""
print_info "View logs:"
print_info "  gcloud run services logs read $SERVICE_NAME --region $REGION"
print_info ""
print_info "API Documentation:"
print_info "  $SERVICE_URL/docs"
print_info ""

if [ "$AUTHENTICATED" = "true" ]; then
    print_warning "Service requires authentication."
    print_info "To call from your backend, use:"
    print_info "  gcloud run services add-iam-policy-binding $SERVICE_NAME \\"
    print_info "    --region=$REGION \\"
    print_info "    --member=serviceAccount:YOUR-BACKEND-SA@$PROJECT_ID.iam.gserviceaccount.com \\"
    print_info "    --role=roles/run.invoker"
fi

print_info ""
print_info "Next steps:"
print_info "1. Update your backend service with RAG_SERVICE_URL=$SERVICE_URL"
print_info "2. Test the /health endpoint"
print_info "3. Test the /chat endpoints from your backend"
