# Airflow Embedding Service

Apache Airflow service for managing data embedding pipelines for the e-commerce RAG chatbot.

## Overview

This service runs scheduled DAGs (Directed Acyclic Graphs) to process and generate embeddings for various e-commerce entities. The DAGs handle daily embedding generation for all tables in both local and cloud PostgreSQL databases, using Google Gemini API for vector embeddings that power semantic search capabilities.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Google API Key (for Gemini AI embeddings)

### Environment Setup

Create a `.env` file in this directory:
```bash
GOOGLE_API_KEY=your_google_api_key_here
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=ecommerce_rag
```

### Running Airflow

```bash
# Start all Airflow services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

Access the Airflow web interface at `http://localhost:8080`
- Username: `admin`
- Password: `admin`

## Services

- **PostgreSQL**: Database with pgvector extension (port 5433)
- **Airflow Webserver**: Web UI (port 8080)
- **Airflow Scheduler**: DAG scheduler
- **Airflow Triggerer**: Event-based triggers
- **Airflow Init**: Database initialization

## Architecture

### Local PostgreSQL DAGs (localhost:5432)
- `product_embedding_dag.py` - Products table (2:00 AM)
- `order_embedding_dag.py` - Orders table (3:00 AM)

### Cloud PostgreSQL DAGs (Google Cloud SQL)
**HIGH Priority (4:00-5:00 AM):**
- `cloud_product_embedding_dag.py` - Products table
- `cloud_product_review_embedding_dag.py` - Product reviews table
- `cloud_order_embedding_dag.py` - Orders table
- `cloud_event_embedding_dag.py` - User events table

**MEDIUM Priority (5:00-6:30 AM):**
- `cloud_category_embedding_dag.py` - Categories table
- `cloud_user_embedding_dag.py` - Users table
- `cloud_order_item_embedding_dag.py` - Order items table
- `cloud_cart_embedding_dag.py` - Shopping carts table
- `cloud_payment_embedding_dag.py` - Payments table
- `cloud_shipment_embedding_dag.py` - Shipments table
- `cloud_inventory_embedding_dag.py` - Inventory table

**LOW Priority (6:30-7:30 AM):**
- `cloud_cart_item_embedding_dag.py` - Cart items table
- `cloud_coupon_embedding_dag.py` - Coupons table
- `cloud_role_embedding_dag.py` - User roles table

## Configuration Management

All DAG configurations are externalized to JSON files in `airflow/config/`:

- **`local_var.json`** - Local PostgreSQL configuration
- **`stg_var.json`** - Cloud PostgreSQL (staging) configuration

**Security:** Credentials are stored in Airflow Connections, NOT in config files.

See [airflow/config/README.md](config/README.md) for detailed configuration instructions.

## DAG Structure

All DAGs follow a consistent 3-task pattern:

1. **Fetch Task:** Query database for records with NULL embeddings
2. **Generate Task:** Preprocess data and generate embeddings via Gemini API
3. **Update Task:** Write embeddings back to database

### Common Features
- Incremental processing (only NULL embeddings)
- Batch processing (100 local, 50 cloud)
- Rate limiting (1 second between batches)
- Error handling and retry logic
- Comprehensive logging
- XCom for inter-task data transfer

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

## Cloud PostgreSQL DAG Details

### Preprocessing Strategies

Each cloud table has a custom preprocessing function in `utils/data_preprocessor.py`:

| Table | Preprocessing Function | Combined Text Format |
|-------|----------------------|---------------------|
| products | `preprocess_cloud_product_records` | name + description + category + price |
| categories | `preprocess_cloud_category_records` | category_name + type + parent hierarchy |
| product_reviews | `preprocess_cloud_review_records` | product + rating + review_text + user |
| users | `preprocess_cloud_user_records` | username + email + job + location + age |
| orders | `preprocess_cloud_order_records` | order_id + status + total + user + date |
| order_items | `preprocess_cloud_order_item_records` | order + product + quantity + price |
| carts | `preprocess_cloud_cart_records` | user + status + total + date |
| cart_items | `preprocess_cloud_cart_item_records` | cart + product + quantity + price |
| payments | `preprocess_cloud_payment_records` | payment_id + amount + method + status |
| shipments | `preprocess_cloud_shipment_records` | tracking + carrier + status + delivery |
| inventory | `preprocess_cloud_inventory_records` | product + warehouse + stock + updated |
| coupons | `preprocess_cloud_coupon_records` | code + discount_type + value + validity |
| events | `preprocess_cloud_event_records` | event_type + user + session + metadata |
| roles | `preprocess_cloud_role_records` | role_name + is_active + created_at |

### Schedule Rationale

**HIGH Priority (4:00-5:00 AM):**
- Customer-facing data (products, reviews, orders)
- User activity tracking (events)
- Critical for search and recommendations

**MEDIUM Priority (5:00-6:30 AM):**
- Supporting data (users, categories, inventory)
- Transactional data (payments, shipments, order items)
- Important but not time-critical

**LOW Priority (6:30-7:30 AM):**
- Reference data (roles, coupons)
- Intermediate data (cart items)
- Low update frequency

### Batch Sizes

- **Local PostgreSQL:** 100 texts/batch (faster local network)
- **Cloud PostgreSQL:** 50 texts/batch (conservative for cloud latency and API limits)

## Utilities Reference

### `utils/embedding_generator.py`

**EmbeddingGenerator Class:**
- `generate_embeddings(texts, batch_size, rate_limit_seconds)` - Batch generate embeddings
- `generate_query_embedding(query)` - Single query embedding
- Uses Google Gemini `models/embedding-001` (768 dimensions)
- Automatic retry logic
- Rate limiting to avoid API throttling

### `utils/data_preprocessor.py`

**DataPreprocessor Class:**

**Local PostgreSQL:**
- `preprocess_product_records(records)` - Local products
- `preprocess_order_records(records)` - Local orders

**Cloud PostgreSQL:**
- `preprocess_cloud_product_records(records)` - Cloud products
- `preprocess_cloud_category_records(records)` - Cloud categories
- `preprocess_cloud_review_records(records)` - Cloud reviews
- `preprocess_cloud_user_records(records)` - Cloud users
- `preprocess_cloud_order_records(records)` - Cloud orders
- `preprocess_cloud_order_item_records(records)` - Cloud order items
- `preprocess_cloud_cart_records(records)` - Cloud carts
- `preprocess_cloud_cart_item_records(records)` - Cloud cart items
- `preprocess_cloud_payment_records(records)` - Cloud payments
- `preprocess_cloud_shipment_records(records)` - Cloud shipments
- `preprocess_cloud_inventory_records(records)` - Cloud inventory
- `preprocess_cloud_coupon_records(records)` - Cloud coupons
- `preprocess_cloud_event_records(records)` - Cloud events
- `preprocess_cloud_role_records(records)` - Cloud roles

All functions return pandas DataFrames with `combined_text` field for embedding.

## Configuration Files

See [airflow/config/README.md](config/README.md) for:
- Configuration file structure
- Setup instructions
- Connection management
- Security best practices
- Schedule overview

## Support

For issues or questions:
1. Check Airflow logs: `~/airflow/logs/` or `docker-compose logs`
2. Review DAG execution logs in Airflow UI
3. Verify database connectivity and data integrity
4. Check configuration files in `airflow/config/`
5. Verify PostgreSQL connections in Airflow UI (Admin → Connections)
6. Consult project documentation in `/docs`

