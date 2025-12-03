# RAG Service

A FastAPI-based Retrieval-Augmented Generation (RAG) chatbot service for e-commerce applications.

## Overview

This service provides AI-powered chat capabilities with role-based access (Admin, User, Visitor) and integrates with a PostgreSQL database with pgvector extension for semantic search.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Google API Key (for Gemini AI)

### Environment Setup

1. Create a `.env` file in this directory:
```bash
GOOGLE_API_KEY=your_google_api_key_here
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=ecommerce_rag
```

### Running the Service

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

The RAG API will be available at `http://localhost:8000`

## Services

- **PostgreSQL**: Database with pgvector extension (port 5432)
- **RAG API**: FastAPI application (port 8000)

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Setup

Run database migrations and setup:

```bash
# Enter the container
docker compose exec rag-api bash

# Run setup scripts
python scripts/migrate_db.py
python scripts/create_chat_history_table.py
```

## Development

For local development without Docker:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn src.api.main:app --reload --port 8000
```

## Project Structure

```
rag-service/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
├── src/
│   ├── api/
│   │   ├── main.py
│   │   └── endpoints/
│   └── rag/
├── static/
├── scripts/
├── data/
└── tests/
```

## Testing

```bash
# Run tests
pytest tests/

# Run specific test file
pytest tests/test_api_endpoints.py
```

## License

See root LICENSE file.
