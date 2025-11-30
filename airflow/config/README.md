# Airflow Configuration Files

This directory contains environment-specific configuration files for Airflow DAGs.

## Configuration Files

### local_var.json
Configuration for local PostgreSQL database (localhost:5432).
- Used by: `product_embedding_dag.py`, `order_embedding_dag.py`
- Connection ID: `postgres_ecommerce_rag`
- Batch size: 100 (higher throughput for local processing)

### stg_var.json
Configuration for cloud PostgreSQL database (Google Cloud SQL).
- Used by: All `cloud_*_embedding_dag.py` files
- Connection ID: `postgres_cloud_ecommerce`
- Batch size: 50 (conservative for cloud API limits)

## Setup Instructions

### 1. Import Variables to Airflow

```bash
# Import local configuration
airflow variables set --file airflow/config/local_var.json local_config

# Import staging configuration
airflow variables set --file airflow/config/stg_var.json stg_config
```

### 2. Configure PostgreSQL Connections

**Local PostgreSQL:**
```bash
airflow connections add 'postgres_ecommerce_rag' \
  --conn-type 'postgres' \
  --conn-host 'localhost' \
  --conn-schema 'ecommerce_rag' \
  --conn-login 'postgres' \
  --conn-password 'YOUR_LOCAL_PASSWORD' \
  --conn-port 5432
```

**Cloud PostgreSQL:**
```bash
airflow connections add 'postgres_cloud_ecommerce' \
  --conn-type 'postgres' \
  --conn-host '34.177.103.63' \
  --conn-schema 'postgres' \
  --conn-login 'postgres' \
  --conn-password 'YOUR_CLOUD_PASSWORD' \
  --conn-port 5432
```

### 3. Set Google API Key

```bash
airflow variables set GOOGLE_API_KEY "YOUR_GEMINI_API_KEY"
```

## Configuration Structure

```json
{
  "description": "Environment description",
  "environment": "local|staging",
  "postgres": {
    "conn_id": "airflow_connection_id",
    "host": "database_host",
    "port": 5432,
    "database": "database_name"
  },
  "embedding": {
    "batch_size": 50,
    "rate_limit_seconds": 1,
    "vector_dimensions": 768,
    "model": "models/embedding-001"
  },
  "schedules": {
    "table_name_embedding": "cron_expression"
  }
}
```

## Security Best Practices

⚠️ **Never commit credentials to version control**

- Database credentials (username/password) are stored in Airflow Connections
- API keys are stored in Airflow Variables
- Configuration files contain only non-sensitive connection metadata
- Use environment variables or secrets management for production

## Usage in DAGs

```python
from airflow.models import Variable
import json

# Load configuration
config = json.loads(Variable.get('stg_config'))

# Access settings
conn_id = config['postgres']['conn_id']
batch_size = config['embedding']['batch_size']
schedule = config['schedules']['product_embedding']
```

## Schedule Overview

### Local (localhost:5432)
- Products: Daily at 2:00 AM
- Orders: Daily at 3:00 AM

### Cloud (34.177.103.63:5432)
**HIGH Priority (4:00-5:00 AM):**
- Products: 4:00 AM
- Product Reviews: 4:00 AM
- Orders: 4:00 AM
- Events: 4:00 AM

**MEDIUM Priority (5:00-6:30 AM):**
- Categories: 5:00 AM
- Users: 5:00 AM
- Order Items: 5:00 AM
- Carts: 6:00 AM
- Payments: 6:00 AM
- Shipments: 6:00 AM
- Inventory: 6:00 AM

**LOW Priority (6:30-7:30 AM):**
- Cart Items: 7:00 AM
- Coupons: 7:00 AM
- Roles: 7:00 AM
