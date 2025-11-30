#!/bin/bash
# Cloud PostgreSQL Embedding Setup Script
# This script configures Airflow for cloud PostgreSQL embedding generation

set -e  # Exit on error

echo "========================================="
echo "Cloud PostgreSQL Embedding Setup"
echo "========================================="
echo ""

# Check if Airflow is installed
if ! command -v airflow &> /dev/null; then
    echo "❌ Error: Airflow is not installed or not in PATH"
    echo "Please install Airflow first: pip install apache-airflow==2.8.0"
    exit 1
fi

echo "✅ Airflow found"

# Get user inputs
echo ""
echo "Please provide the following credentials:"
echo "(These will be stored securely in Airflow, NOT in code)"
echo ""

read -p "Cloud PostgreSQL Password: " -s CLOUD_DB_PASSWORD
echo ""
read -p "Google Gemini API Key: " -s GOOGLE_API_KEY
echo ""

# Import configuration files
echo ""
echo "📦 Importing configuration files..."

if [ ! -f "airflow/config/local_var.json" ]; then
    echo "❌ Error: airflow/config/local_var.json not found"
    exit 1
fi

if [ ! -f "airflow/config/stg_var.json" ]; then
    echo "❌ Error: airflow/config/stg_var.json not found"
    exit 1
fi

airflow variables set --file airflow/config/local_var.json local_config
echo "✅ Imported local_config"

airflow variables set --file airflow/config/stg_var.json stg_config
echo "✅ Imported stg_config"

# Set Google API key
airflow variables set GOOGLE_API_KEY "$GOOGLE_API_KEY"
echo "✅ Set GOOGLE_API_KEY"

# Configure cloud PostgreSQL connection
echo ""
echo "🔗 Configuring cloud PostgreSQL connection..."

airflow connections delete 'postgres_cloud_ecommerce' 2>/dev/null || true

airflow connections add 'postgres_cloud_ecommerce' \
  --conn-type 'postgres' \
  --conn-host '34.177.103.63' \
  --conn-schema 'postgres' \
  --conn-login 'postgres' \
  --conn-password "$CLOUD_DB_PASSWORD" \
  --conn-port 5432

echo "✅ Created postgres_cloud_ecommerce connection"

# Verify setup
echo ""
echo "🔍 Verifying setup..."

# Check variables
if airflow variables get local_config &>/dev/null; then
    echo "✅ local_config variable exists"
else
    echo "❌ local_config variable not found"
fi

if airflow variables get stg_config &>/dev/null; then
    echo "✅ stg_config variable exists"
else
    echo "❌ stg_config variable not found"
fi

if airflow variables get GOOGLE_API_KEY &>/dev/null; then
    echo "✅ GOOGLE_API_KEY variable exists"
else
    echo "❌ GOOGLE_API_KEY variable not found"
fi

# Count cloud DAGs
CLOUD_DAG_COUNT=$(ls -1 airflow/dags/cloud_*.py 2>/dev/null | wc -l)
echo "✅ Found $CLOUD_DAG_COUNT cloud DAG files"

# Summary
echo ""
echo "========================================="
echo "Setup Complete! 🎉"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Start Airflow:"
echo "   docker-compose up -d"
echo "   OR"
echo "   airflow webserver & airflow scheduler &"
echo ""
echo "2. Access Airflow UI:"
echo "   http://localhost:8080"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "3. Enable cloud DAGs in the UI"
echo ""
echo "4. Run database setup SQL:"
echo "   psql -h 34.177.103.63 -U postgres -d postgres"
echo "   Then execute the SQL from CLOUD_EMBEDDING_IMPLEMENTATION.md"
echo ""
echo "5. Manually trigger a test DAG:"
echo "   cloud_product_embedding_generation"
echo ""
echo "For detailed instructions, see:"
echo "- airflow/README.md"
echo "- airflow/config/README.md"
echo "- CLOUD_EMBEDDING_IMPLEMENTATION.md"
echo ""
