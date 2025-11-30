# Airflow DAGs for E-commerce RAG Chatbot

This directory contains Airflow DAGs for automated embedding generation and data processing for the E-commerce RAG Chatbot system.

## Overview

The DAGs handle daily embedding generation for products and orders stored in PostgreSQL, using Google Gemini API for vector embeddings that power semantic search capabilities.

## DAGs

### 1. `product_embedding_dag.py`
- **Schedule:** Daily at 2:00 AM UTC
- **Purpose:** Generate embeddings for products with NULL embeddings
- **Tasks:**
  1. Fetch products without embeddings from PostgreSQL
  2. Preprocess product data (create combined_text from title, description, category)
  3. Generate 768-dimensional embeddings using Gemini API (batch size: 100)
  4. Update products table with new embeddings
  5. Log summary statistics

### 2. `order_embedding_dag.py`
- **Schedule:** Daily at 3:00 AM UTC
- **Purpose:** Generate embeddings for orders with NULL embeddings
- **Tasks:**
  1. Fetch orders without embeddings from PostgreSQL
  2. Preprocess order data (create text from product, category, priority)
  3. Generate 768-dimensional embeddings using Gemini API (batch size: 100)
  4. Update orders table with new embeddings
  5. Log summary statistics

## Utilities

### `utils/embedding_generator.py`
- `EmbeddingGenerator` class: Handles Gemini API integration
- Batch processing (100 texts per API call)
- Rate limiting (1 second between batches)
- Error handling and logging

### `utils/data_preprocessor.py`
- `DataPreprocessor` class: Handles data preprocessing
- `preprocess_product_records()`: Creates combined_text for products
- `preprocess_order_records()`: Creates embedding_text for orders
- Includes CSV preprocessing functions for backward compatibility

## Setup Instructions

### Option 1: Using Docker Compose (Recommended)

#### 1. Set Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:
```env
GOOGLE_API_KEY=your_actual_google_api_key_here
```

#### 2. Start All Services

From the project root directory:

```bash
# Build and start all services (PostgreSQL + Airflow)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f airflow-webserver
docker-compose logs -f airflow-scheduler
```

#### 3. Access Airflow UI

1. Open browser: http://localhost:8080
2. Login credentials:
   - **Username:** `admin`
   - **Password:** `admin`

#### 4. Verify DAGs

The DAGs should automatically appear in the Airflow UI:
- `product_embedding_generation`
- `order_embedding_generation`

Enable them by toggling the switch on the left side of each DAG.

#### 5. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

### Option 2: Manual Airflow Installation

#### 1. Install Airflow Dependencies

```bash
pip install apache-airflow==2.8.0
pip install apache-airflow-providers-postgres==5.10.0
pip install google-generativeai
pip install pandas
pip install psycopg2-binary
```

#### 2. Configure PostgreSQL Connection

In the Airflow UI, create a PostgreSQL connection:

1. Navigate to **Admin → Connections**
2. Click **+** to add a new connection
3. Configure:
   - **Connection Id:** `postgres_ecommerce_rag`
   - **Connection Type:** `Postgres`
   - **Host:** `localhost` (or your PostgreSQL host)
   - **Schema:** `ecommerce_rag`
   - **Login:** `postgres` (your DB user)
   - **Password:** Your database password
   - **Port:** `5432`

**Alternative: Using Environment Variables**

Set in your Airflow environment:
```bash
export AIRFLOW_CONN_POSTGRES_ECOMMERCE_RAG='postgresql://postgres:password@localhost:5432/ecommerce_rag'
```

### 3. Configure Google API Key

In the Airflow UI, create a variable for the Google API key:

1. Navigate to **Admin → Variables**
2. Click **+** to add a new variable
3. Configure:
   - **Key:** `GOOGLE_API_KEY`
   - **Value:** Your Google API key for Gemini

**Alternative: Using Environment Variables**

Set in your Airflow environment:
```bash
export AIRFLOW_VAR_GOOGLE_API_KEY='your_google_api_key_here'
```

### 4. Deploy DAGs

Copy the DAG files to your Airflow DAGs folder:

```bash
# Default Airflow DAGs folder
cp -r airflow/dags/* ~/airflow/dags/

# Or set AIRFLOW_HOME and copy
export AIRFLOW_HOME=/path/to/your/airflow
cp -r airflow/dags/* $AIRFLOW_HOME/dags/
```

### 5. Verify DAG Setup

1. Start Airflow:
   ```bash
   airflow webserver --port 8080
   airflow scheduler
   ```

2. Access Airflow UI at http://localhost:8080

3. Check that DAGs appear:
   - `product_embedding_generation`
   - `order_embedding_generation`

4. Enable the DAGs by toggling them on

## Usage

### Manual Trigger

To trigger a DAG manually:

1. Go to Airflow UI
2. Find the DAG (`product_embedding_generation` or `order_embedding_generation`)
3. Click the **▶** (play) button on the right
4. Confirm trigger

### Monitor Execution

1. Click on the DAG name to view details
2. View the **Graph View** to see task dependencies
3. Click on individual tasks to view logs
4. Check the **Log** tab for detailed execution information

### View Logs

Logs include:
- Number of records fetched without embeddings
- Preprocessing results
- Embedding generation progress (batch by batch)
- Database update results
- Summary statistics

Example log output:
```
[2025-11-30 02:00:05] INFO - Fetching products without embeddings...
[2025-11-30 02:00:06] INFO - Found 150 products without embeddings
[2025-11-30 02:00:07] INFO - Processing batch 1/2 (100 texts)
[2025-11-30 02:00:15] INFO - Processing batch 2/2 (50 texts)
[2025-11-30 02:00:20] INFO - Successfully generated 150 embeddings
[2025-11-30 02:00:22] INFO - Successfully updated 150 product embeddings
[2025-11-30 02:00:22] INFO - ============================================================
[2025-11-30 02:00:22] INFO - PRODUCT EMBEDDING GENERATION SUMMARY
[2025-11-30 02:00:22] INFO - ============================================================
[2025-11-30 02:00:22] INFO - Products found without embeddings: 150
[2025-11-30 02:00:22] INFO - Embeddings generated: 150
[2025-11-30 02:00:22] INFO - Database records updated: 150
[2025-11-30 02:00:22] INFO - ============================================================
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Airflow Scheduler                     │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┴────────────────┐
           │                                │
┌──────────▼──────────┐        ┌───────────▼────────────┐
│  Product Embedding  │        │   Order Embedding      │
│       DAG           │        │        DAG             │
│  (Daily 2 AM)       │        │   (Daily 3 AM)         │
└──────────┬──────────┘        └───────────┬────────────┘
           │                                │
           │  1. Fetch NULL embeddings      │
           │  2. Preprocess data            │
           │  3. Generate embeddings        │
           │  4. Update database            │
           │                                │
           └───────────────┬────────────────┘
                           │
                  ┌────────▼─────────┐
                  │   PostgreSQL     │
                  │  (with pgvector) │
                  │                  │
                  │  - products      │
                  │  - orders        │
                  └──────────────────┘
```

## Database Schema

### Products Table
```sql
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_title TEXT,
    description TEXT,
    category TEXT,
    price FLOAT,
    rating FLOAT,
    rating_count INTEGER,
    store TEXT,
    feature_list TEXT[],
    combined_text TEXT,
    embedding vector(768)  -- Generated by DAG
);
```

### Orders Table
```sql
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    order_datetime TIMESTAMP,
    customer_id TEXT,
    gender TEXT,
    device_type TEXT,
    customer_login_type TEXT,
    product_category TEXT,
    product TEXT,
    quantity INTEGER,
    sales FLOAT,
    total_amount FLOAT,
    discount FLOAT,
    profit FLOAT,
    net_profit FLOAT,
    shipping_cost FLOAT,
    order_priority TEXT,
    payment_method TEXT,
    embedding vector(768)  -- Generated by DAG
);
```

## Troubleshooting

### DAGs Not Appearing

1. Check DAG folder path: `airflow config list | grep dags_folder`
2. Verify DAG files are in the correct folder
3. Check for Python syntax errors: `python airflow/dags/product_embedding_dag.py`
4. Restart Airflow scheduler

### Connection Errors

1. Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
2. Check connection in Airflow UI: **Admin → Connections**
3. Test connection from Python:
   ```python
   import psycopg2
   conn = psycopg2.connect(
       host='localhost',
       port=5432,
       user='postgres',
       password='password',
       dbname='ecommerce_rag'
   )
   ```

### API Key Errors

1. Verify variable exists: **Admin → Variables** → `GOOGLE_API_KEY`
2. Test API key:
   ```python
   import google.generativeai as genai
   genai.configure(api_key='your_key')
   result = genai.embed_content(
       model="models/embedding-001",
       content="test"
   )
   ```

### Import Errors

If you see import errors in DAG files:
1. Ensure all dependencies are installed in the Airflow environment
2. Check Python path includes the DAGs directory
3. Verify `utils` folder is in the same directory as DAG files

### Rate Limiting

If you hit API rate limits:
1. Reduce batch size in `EmbeddingGenerator` (default: 100)
2. Increase sleep time between batches (default: 1 second)
3. Schedule DAGs at different times to avoid overlap

## Monitoring and Maintenance

### Daily Checks

1. Monitor DAG run history in Airflow UI
2. Check for failed tasks
3. Review embedding generation counts in logs
4. Verify database updates completed successfully

### Performance Metrics

Track these metrics over time:
- Number of records processed daily
- Embedding generation time
- API call success rate
- Database update performance

### Optimization

Consider these optimizations:
1. **Batch Size:** Adjust based on API limits and performance
2. **Parallel Processing:** Split large datasets into parallel tasks
3. **Incremental Processing:** Add timestamp columns to track updates
4. **Retry Logic:** Configure retry attempts and delays
5. **Alerting:** Set up email/Slack notifications for failures

## Additional Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Provider Documentation](https://airflow.apache.org/docs/apache-airflow-providers-postgres/)

## Docker Compose Architecture

The `docker-compose.yml` file in the project root defines the complete infrastructure:

### Services

1. **postgres** (pgvector/pgvector:pg16)
   - PostgreSQL database with vector extension
   - Port: 5432
   - Volume: `postgres_data` for persistence
   - Healthcheck enabled

2. **airflow-init**
   - One-time initialization service
   - Creates database schema
   - Creates admin user (admin/admin)
   - Exits after completion

3. **airflow-webserver**
   - Web interface for Airflow
   - Port: 8080
   - Healthcheck: HTTP endpoint
   - Restart policy: always

4. **airflow-scheduler**
   - Schedules and executes DAGs
   - Monitors DAG files
   - Healthcheck: scheduler job status
   - Restart policy: always

5. **airflow-triggerer**
   - Handles deferred/async tasks
   - Healthcheck: triggerer job status
   - Restart policy: always

### Volumes

- **postgres_data**: PostgreSQL data persistence
- **airflow_logs**: Airflow task execution logs

### Networks

- **ecommerce_network**: Bridge network for inter-service communication

### Environment Variables

All Airflow services share common environment variables:
- `AIRFLOW__CORE__EXECUTOR=LocalExecutor`: Single-node execution
- `AIRFLOW__CORE__SQL_ALCHEMY_CONN`: PostgreSQL connection string
- `GOOGLE_API_KEY`: For Gemini API access
- `DB_*`: Database connection details
- `PYTHONPATH`: Includes src and scripts for DAG access

### Mounted Volumes

Each Airflow service mounts:
- `./airflow/dags`: DAG files
- `./airflow/plugins`: Custom plugins
- `./airflow/config`: Configuration files
- `./src`: Source code (for imports)
- `./scripts`: Utility scripts
- `./data`: Data directory
- `airflow_logs`: Logs volume

### Building Custom Image

The Airflow services use a custom Dockerfile (`Dockerfile.airflow`) that:
1. Extends official Airflow 2.8.0 image (Python 3.11)
2. Installs project dependencies from `requirements.txt`
3. Adds PostgreSQL provider and Google Generative AI packages
4. Configures working directory

To rebuild the images:
```bash
docker-compose build
docker-compose up -d
```

## Support

For issues or questions:
1. Check Airflow logs: `~/airflow/logs/` or `docker-compose logs`
2. Review DAG execution logs in Airflow UI
3. Verify database connectivity and data integrity
4. Consult project documentation in `/docs`
