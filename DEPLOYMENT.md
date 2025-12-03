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
