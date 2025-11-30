# E-commerce RAG Chatbot

A chatbot leveraging **RAG (Retrieval-Augmented Generation)** with PostgreSQL + pgvector for semantic search and Google Gemini for embeddings/LLM.

## Tech Stack

- **Database**: PostgreSQL 16 + pgvector
- **Embeddings**: Google Gemini `embedding-001` (768 dimensions)
- **LLM**: Google Gemini `gemini-2.5-flash-lite`
- **API**: FastAPI
- **Pipeline**: Apache Airflow 2.8.0

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Google API Key ([Get one here](https://makersuite.google.com/app/apikey))

## Quick Start

### 1. Environment Setup

```bash
cd Ecommerce-RAG-Chatbot
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

**`.env` file:**
```env
GOOGLE_API_KEY=your_google_api_key
DB_HOST=localhost
DB_PORT=5432
DB_USER=rag_user
DB_PASSWORD=rag_password
DB_NAME=ecommerce_rag
```

### 2. Start PostgreSQL

```bash
docker-compose up -d postgres
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Database & Load Data

**Prepare data files** in `data/raw/`:
- `Product_Information_Dataset.csv`
- `Order_Data_Dataset.csv`

**Run migration:**
```bash
python scripts/migrate_db.py
```

This will:
- Create tables with pgvector extension
- Load and preprocess CSV data
- Generate embeddings via Gemini API
- Insert data into PostgreSQL

### 5. Start API Server

```bash
python scripts/run.py api
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Web Chat: http://localhost:8000/static/index.html
```

## Project Structure

```
├── airflow/
│   └── dags/                   # Airflow DAGs (optional)
├── data/
│   └── raw/                    # Raw CSV files
├── scripts/
│   ├── migrate_db.py           # Database setup & migration
│   ├── create_chat_history_table.py
│   └── run.py                  # Run API server
├── src/
│   ├── api/                    # FastAPI endpoints
│   ├── etl/                    # ETL modules
│   └── rag/                    # RAG assistant
├── static/                     # Web UI
├── docker-compose.yml
└── requirements.txt
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/message` | Send message to chatbot |
| GET | `/products/search` | Search products |
| GET | `/orders/customer/{id}` | Get customer orders |

## Using Airflow (Optional)

```bash
docker-compose up -d
# Airflow UI: http://localhost:8080 (admin/admin)
```

**Available DAGs:**
- `embedding_pipeline_dag`: Generate embeddings (configurable: process_from, process_to, batch_size)
- `data_ingestion_dag`: Daily data loading
- `maintenance_dag`: Weekly cleanup

## Troubleshooting

**Database connection error:**
```bash
docker-compose ps
docker-compose logs postgres
```

**Embedding errors:**
- Verify `GOOGLE_API_KEY` is set correctly
- Check API quota at [Google Cloud Console](https://console.cloud.google.com/apis/dashboard)