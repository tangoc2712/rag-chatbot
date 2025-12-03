# E-commerce RAG Chatbot

An AI-powered chatbot system leveraging **RAG (Retrieval-Augmented Generation)** with PostgreSQL + pgvector for semantic search and Google Gemini for embeddings/LLM.

> **📦 New Microservices Architecture:** This project has been restructured into independent services. See [MIGRATION.md](MIGRATION.md) for details.

## Project Structure

This repository contains two independent services:

### 🤖 RAG Service (`services/rag-service/`)
The main chatbot API service with role-based access (Admin, User, Visitor) for querying e-commerce data.
- FastAPI-based REST API
- PostgreSQL with pgvector for semantic search
- Google Gemini for embeddings and LLM
- Standalone deployment ready

**[→ View RAG Service Documentation](services/rag-service/README.md)**

### ⚙️ Airflow Service (`services/airflow/`)
Background embedding generation pipeline using Apache Airflow for processing and updating vector embeddings.
- Apache Airflow 2.8.0
- Scheduled DAGs for embedding generation
- Support for multiple entity types
- Independent deployment

**[→ View Airflow Service Documentation](services/airflow/README.md)**

## Quick Start

Each service can be deployed independently:

### Deploy RAG Service Only

```bash
cd services/rag-service
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
docker compose up -d
```

Access at `http://localhost:8000`

### Deploy Airflow Service Only

```bash
cd services/airflow
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
docker compose up -d
```

Access at `http://localhost:8080`

## Key Features

- 🔑 **Role-Based Access** - Admin, User, and Visitor modes with different permissions
- 🧠 **Intelligent Query Routing** - Automatically detects intent and routes to SQL or semantic search
- 📊 **Multi-Table Support** - Access to 14+ tables including products, orders, users, payments, and more
- 💬 **Natural Language Interface** - Ask questions in plain English
- ⚡ **Real-time Analysis** - Get instant insights on sales, inventory, customer behavior
- 🔄 **Automated Embeddings** - Scheduled pipeline for keeping embeddings up-to-date

## Supported Tables

The system supports:
- **Products** - Product catalog with descriptions, prices, ratings
- **Users** - Customer profiles and information
- **Orders** - Order history and status
- **Order Items** - Detailed order line items
- **Payments** - Payment transactions and status
- **Shipments** - Shipping tracking and delivery status
- **Inventory** - Stock levels and warehouse locations
- **Product Reviews** - Customer ratings and feedback
- **Carts & Cart Items** - Shopping cart data
- **Coupons** - Discount codes and promotions
- **Categories** - Product categorization
- **Roles** - User role management
- **Events** - User activity tracking

## Tech Stack

- **Database**: PostgreSQL 16 + pgvector
- **Embeddings**: Google Gemini `embedding-001` (768 dimensions)
- **LLM**: Google Gemini `gemini-2.5-flash-lite`
- **API**: FastAPI
- **Pipeline**: Apache Airflow 2.8.0
- **Deployment**: Docker & Docker Compose

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

## Development

For detailed development instructions, see the service-specific documentation:
- [RAG Service Development](services/rag-service/README.md)
- [Airflow Service Development](services/airflow/README.md)

## Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide for both services
- **[MIGRATION.md](MIGRATION.md)** - Project restructuring details and migration guide
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Full API reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Google API Key ([Get one here](https://makersuite.google.com/app/apikey))

## Contributing

1. Each service is independent - work on them separately
2. Follow the service-specific README for development setup
3. Test changes in isolation before deployment

## License

See LICENSE file for details.
