# Deployment Guide

This guide explains how to deploy each service independently.

## Service Overview

```
rag-chatbot/
├── services/
│   ├── rag-service/          # FastAPI chatbot service
│   └── airflow/              # Embedding pipeline service
├── README.md                 # Project overview
├── API_DOCUMENTATION.md      # API reference
└── ARCHITECTURE.md          # Architecture documentation
```

## RAG Service Deployment

The RAG service provides the chatbot API and web interface.

### Prerequisites
- Docker and Docker Compose
- Google API Key

### Steps

1. **Navigate to service directory:**
   ```bash
   cd services/rag-service
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set your GOOGLE_API_KEY
   ```

3. **Deploy with Docker:**
   ```bash
   docker compose up -d
   ```

4. **Access the service:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Web UI: http://localhost:8000/static/index.html

5. **Setup database (first time only):**
   ```bash
   docker compose exec rag-api bash
   python scripts/migrate_db.py
   python scripts/create_chat_history_table.py
   exit
   ```

### Useful Commands
```bash
# View logs
docker compose logs -f

# Stop service
docker compose down

# Restart service
docker compose restart

# Remove all data (including database)
docker compose down -v
```

## Airflow Service Deployment

The Airflow service manages embedding generation pipelines.

### Prerequisites
- Docker and Docker Compose
- Google API Key

### Steps

1. **Navigate to service directory:**
   ```bash
   cd services/airflow
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set your GOOGLE_API_KEY
   ```

3. **Deploy with Docker:**
   ```bash
   docker compose up -d
   ```

4. **Access Airflow:**
   - Web UI: http://localhost:8080
   - Username: `admin`
   - Password: `admin`

5. **Enable DAGs:**
   - Navigate to the Airflow UI
   - Toggle ON the DAGs you want to run

### Useful Commands
```bash
# View logs
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-webserver

# Stop service
docker compose down

# Restart scheduler
docker compose restart airflow-scheduler

# Remove all data
docker compose down -v
```

## Deploying Both Services

If you need both services running:

### Option 1: Separate Terminals
```bash
# Terminal 1 - RAG Service
cd services/rag-service
docker compose up

# Terminal 2 - Airflow Service
cd services/airflow
docker compose up
```

### Option 2: Detached Mode
```bash
# Start RAG service
cd services/rag-service
docker compose up -d

# Start Airflow service
cd ../airflow
docker compose up -d
```

## Port Configuration

Default ports used:
- **RAG Service:**
  - API: 8000
  - PostgreSQL: 5432

- **Airflow Service:**
  - Web UI: 8080
  - PostgreSQL: 5433 (different from RAG service)

If ports conflict, edit the `docker-compose.yml` in each service directory.

## Database Considerations

Each service has its own PostgreSQL instance by default. If you want to share a database:

1. Use the RAG service database
2. Update Airflow's `docker-compose.yml` to point to the RAG service database
3. Change the network configuration to allow communication

## Environment Variables

Both services use similar environment variables:

```bash
GOOGLE_API_KEY=your_google_api_key_here
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=ecommerce_rag
```

## Production Deployment

For production:

1. **Use strong passwords** - Change default PostgreSQL passwords
2. **Set Fernet key** for Airflow (in Airflow's docker-compose.yml)
3. **Use secrets management** - Don't commit .env files
4. **Configure backups** - Set up database backup strategies
5. **Enable SSL/TLS** - For API endpoints
6. **Use reverse proxy** - Nginx or Traefik in front of services
7. **Monitor resources** - Set up monitoring and alerting

## Cloud Run Deployment (RAG Service)

Deploy the RAG service to Google Cloud Run for production-grade hosting that your backend can call.

### Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Cloud SQL PostgreSQL instance** (recommended for production)
4. **Required APIs enabled:**
   ```bash
   gcloud services enable \
     cloudbuild.googleapis.com \
     run.googleapis.com \
     secretmanager.googleapis.com \
     sqladmin.googleapis.com
   ```

### Database Setup

#### Option 1: Cloud SQL (Recommended for Production)

1. **Create Cloud SQL instance:**
   ```bash
   gcloud sql instances create rag-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=asia-southeast1 \
     --root-password=YOUR_SECURE_PASSWORD
   ```

2. **Install pgvector extension:**
   ```bash
   gcloud sql instances patch rag-db \
     --database-flags=cloudsql.enable_pgvector=on
   ```

3. **Create database:**
   ```bash
   gcloud sql databases create ecommerce_rag --instance=rag-db
   ```

4. **Store password in Secret Manager:**
   ```bash
   echo -n "YOUR_SECURE_PASSWORD" | gcloud secrets create db-password --data-file=-
   ```

5. **Get connection name:**
   ```bash
   gcloud sql instances describe rag-db --format='value(connectionName)'
   # Output: PROJECT_ID:REGION:INSTANCE_NAME
   ```

#### Option 2: External PostgreSQL

If using an external database (like your existing setup), ensure it's accessible from Cloud Run.

### Environment Configuration

1. **Set environment variables:**
   ```bash
   export GCP_PROJECT_ID="your-project-id"
   export GCP_REGION="asia-southeast1"
   export DB_HOST="PROJECT_ID:REGION:INSTANCE_NAME"  # For Cloud SQL
   export DB_PASSWORD_SECRET="db-password"  # Secret Manager name
   export GOOGLE_API_KEY="your-google-api-key"
   ```

2. **For Cloud SQL connection:**
   ```bash
   export USE_CLOUD_SQL_SOCKET="true"
   export CLOUD_SQL_CONNECTION_NAME="PROJECT_ID:REGION:INSTANCE_NAME"
   ```

### Deploy Using Script

Navigate to the RAG service directory:
```bash
cd services/rag-service
```

#### Public Access (for testing):
```bash
./deploy.sh --project YOUR_PROJECT_ID --region asia-southeast1
```

#### Authenticated Access (recommended for production):
```bash
./deploy.sh --project YOUR_PROJECT_ID --region asia-southeast1 --authenticated
```

### Manual Deployment

If you prefer manual deployment:

```bash
cd services/rag-service

# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/rag-service

# Deploy to Cloud Run
gcloud run deploy rag-service \
  --image gcr.io/YOUR_PROJECT_ID/rag-service \
  --region asia-southeast1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars "DB_HOST=YOUR_DB_HOST,DB_PORT=5432,DB_USER=postgres,DB_NAME=ecommerce_rag,GOOGLE_API_KEY=YOUR_API_KEY" \
  --set-secrets "DB_PASSWORD=db-password:latest" \
  --add-cloudsql-instances "PROJECT_ID:REGION:INSTANCE_NAME"
```

### Connect Backend to RAG Service

#### For Public RAG Service:
Your backend can call directly:
```python
import requests

RAG_SERVICE_URL = "https://rag-service-xxxxx-xx.a.run.app"

response = requests.post(
    f"{RAG_SERVICE_URL}/chat/admin",
    json={"message": "What are the top selling products?"}
)
```

#### For Authenticated RAG Service:
Your backend needs to send an identity token:

```python
import google.auth.transport.requests
import google.oauth2.id_token

def call_rag_service(message: str, role: str = "admin"):
    """Call authenticated Cloud Run RAG service"""
    
    RAG_SERVICE_URL = "https://rag-service-xxxxx-xx.a.run.app"
    
    # Get identity token
    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, RAG_SERVICE_URL)
    
    # Make authenticated request
    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{RAG_SERVICE_URL}/chat/{role}",
        json={"message": message},
        headers=headers
    )
    
    return response.json()
```

#### Grant Backend Service Account Access:
```bash
# Get your backend service account
BACKEND_SA="your-backend-service@YOUR_PROJECT_ID.iam.gserviceaccount.com"

# Grant invoker role
gcloud run services add-iam-policy-binding rag-service \
  --region=asia-southeast1 \
  --member="serviceAccount:$BACKEND_SA" \
  --role="roles/run.invoker"
```

### Initialize Database

After first deployment, initialize the database:

```bash
# Get a shell in Cloud Run (for setup only)
gcloud run services proxy rag-service --region=asia-southeast1 &
PROXY_PID=$!

# Run migrations
curl -X POST http://localhost:8080/admin/migrate

# Or use Cloud Run Jobs for one-time setup
gcloud run jobs create rag-db-setup \
  --image gcr.io/YOUR_PROJECT_ID/rag-service \
  --region asia-southeast1 \
  --set-env-vars "DB_HOST=..." \
  --command "python" \
  --args "scripts/migrate_db.py"

gcloud run jobs execute rag-db-setup --region asia-southeast1

kill $PROXY_PID
```

### Monitoring and Logs

```bash
# View logs
gcloud run services logs read rag-service --region asia-southeast1

# Follow logs
gcloud run services logs tail rag-service --region asia-southeast1

# View metrics in Cloud Console
gcloud run services describe rag-service --region asia-southeast1
```

### Service URL

After deployment, get your service URL:
```bash
gcloud run services describe rag-service \
  --region asia-southeast1 \
  --format='value(status.url)'
```

### Testing the Deployment

```bash
# Health check
curl https://rag-service-xxxxx-xx.a.run.app/health

# API documentation
curl https://rag-service-xxxxx-xx.a.run.app/docs

# Test chat endpoint
curl -X POST https://rag-service-xxxxx-xx.a.run.app/chat/admin \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top selling products?"}'
```

### Cost Optimization

1. **Set min instances to 0** - Only pay when service is used
2. **Configure appropriate memory/CPU** - Start with 2Gi/2 CPU
3. **Set max instances** - Prevent runaway costs
4. **Use Cloud SQL Proxy** - More secure than public IP
5. **Enable request/response compression**

### Security Best Practices

1. **Use Secret Manager** for sensitive data
2. **Enable authentication** for production
3. **Use Cloud SQL with private IP** 
4. **Implement rate limiting** in your backend
5. **Use VPC Connector** for private networking
6. **Enable Cloud Armor** for DDoS protection

### Updating the Service

```bash
cd services/rag-service

# Deploy updates
./deploy.sh --project YOUR_PROJECT_ID

# Or manually
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/rag-service
gcloud run deploy rag-service \
  --image gcr.io/YOUR_PROJECT_ID/rag-service \
  --region asia-southeast1
```

### Rollback

```bash
# List revisions
gcloud run revisions list --service rag-service --region asia-southeast1

# Rollback to previous revision
gcloud run services update-traffic rag-service \
  --region asia-southeast1 \
  --to-revisions REVISION_NAME=100
```

## Troubleshooting

### RAG Service Won't Start
```bash
# Check logs
docker compose logs rag-api

# Verify database is healthy
docker compose ps

# Check port availability
lsof -i :8000
```

### Airflow Service Issues
```bash
# Check scheduler logs
docker compose logs airflow-scheduler

# Verify initialization completed
docker compose logs airflow-init

# Reset Airflow database
docker compose down -v
docker compose up -d
```

### Database Connection Errors
```bash
# Verify database is running
docker compose ps postgres

# Check database logs
docker compose logs postgres

# Test connection
docker compose exec postgres psql -U postgres -d ecommerce_rag
```

## Updating Services

To update a service:

```bash
# Pull latest code
git pull

# Navigate to service
cd services/rag-service  # or services/airflow

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Clean Installation

To completely reset a service:

```bash
cd services/rag-service  # or services/airflow

# Stop and remove everything
docker compose down -v

# Remove images
docker compose down --rmi all -v

# Start fresh
docker compose up -d
```

## Support

For issues or questions:
1. Check service-specific README files
2. Review logs using `docker compose logs`
3. See API_DOCUMENTATION.md for API details
4. See ARCHITECTURE.md for system design
