# E-commerce RAG Chatbot - Admin Mode

An AI-powered database assistant with **ADMIN-level access** leveraging **RAG (Retrieval-Augmented Generation)** with PostgreSQL + pgvector for semantic search and Google Gemini for embeddings/LLM.

## Key Features

- 🔑 **Full Admin Access** - Query any data across all tables without restrictions
- 🧠 **Intelligent Query Routing** - Automatically detects intent and routes to SQL or semantic search
- 📊 **Multi-Table Support** - Access to 14+ tables including products, orders, users, payments, shipments, reviews, and more
- 💬 **Natural Language Interface** - Ask questions in plain English
- ⚡ **Real-time Analysis** - Get instant insights on sales, inventory, customer behavior, and more

## Supported Tables

The chatbot has full access to:
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

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/message` | Send message to chatbot (admin access) |
| GET | `/chat/history/{session_id}` | Get chat history |

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products/search` | Search products semantically |
| GET | `/products/{product_id}` | Get product details |
| GET | `/products/` | List all products |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/{user_id}` | Get user details |
| GET | `/users/` | List all users |
| GET | `/users/search` | Search users |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders/{order_id}` | Get order details |
| GET | `/orders/` | List all orders |
| GET | `/orders/user/{user_id}` | Get user's orders |

### Other Endpoints
- `/categories/*` - Category management
- `/reviews/*` - Product reviews
- `/inventory/*` - Stock management
- `/payments/*` - Payment tracking
- `/shipments/*` - Shipment tracking
- `/coupons/*` - Coupon management

## Example Queries

The admin chatbot can answer questions like:

**Sales & Revenue:**
- "What's our total revenue this month?"
- "Show me the top 10 selling products"
- "How many orders are pending?"

**Inventory:**
- "What products are low in stock?"
- "Show me products with 0 inventory"

**Customer Insights:**
- "How many new users registered this week?"
- "Who are our top customers by order value?"
- "Show me users with the most orders"

**Product Analysis:**
- "What are the highest rated products?"
- "Find products with negative reviews"
- "Show me products in the electronics category"

**Operations:**
- "List pending shipments"
- "Show payment failures today"
- "What coupons are currently active?"

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