#!/bin/bash

# Quick Deploy Script for hackathon-478514
# Uses existing Cloud SQL database

set -e

# Your project configuration
export GCP_PROJECT_ID="hackathon-478514"
export GCP_REGION="asia-southeast1"

# Database configuration - UPDATE THESE VALUES
# Get your Cloud SQL connection name from: gcloud sql instances list
export DB_CONNECTION_NAME="hackathon-478514:asia-southeast1:YOUR_INSTANCE_NAME"
export DB_NAME="ecommerce_rag"
export DB_USER="postgres"
export DB_PASSWORD_SECRET="db-password"  # Secret Manager secret name

# Google API Key - UPDATE THIS
export GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"

# Deployment options
AUTHENTICATED=""  # Add "--authenticated" for production with auth

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}RAG Service Deployment${NC}"
echo -e "${GREEN}Project: hackathon-478514${NC}"
echo -e "${GREEN}Region: asia-southeast1${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if variables are set
if [[ "$DB_CONNECTION_NAME" == *"YOUR_INSTANCE_NAME"* ]]; then
    echo -e "${YELLOW}⚠️  Please update DB_CONNECTION_NAME in this script${NC}"
    echo "Run: gcloud sql instances list"
    exit 1
fi

if [[ "$GOOGLE_API_KEY" == "YOUR_GOOGLE_API_KEY" ]]; then
    echo -e "${YELLOW}⚠️  Please set your GOOGLE_API_KEY in this script${NC}"
    exit 1
fi

echo "Database: $DB_CONNECTION_NAME"
echo "Deploying..."
echo ""

# Deploy using the main script
./deploy.sh \
    --project "$GCP_PROJECT_ID" \
    --region "$GCP_REGION" \
    $AUTHENTICATED

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Test the service health endpoint"
echo "2. Update your backend with the RAG_SERVICE_URL"
echo "3. Test chat endpoints from your backend"
