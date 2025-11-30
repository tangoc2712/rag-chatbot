# System Architecture

This document outlines the system architecture of the E-Commerce RAG Chatbot project, including its components, data flow, and data lineage.

## System Overview

The E-Commerce RAG Chatbot is designed to provide intelligent product search and order management capabilities. The system operates in two main modes:
1.  **REST API**: A FastAPI-based service providing structured access to product and order data.
2.  **RAG Chat Interface**: A conversational assistant that uses Retrieval-Augmented Generation (RAG) with PostgreSQL + pgvector for semantic search and Google Gemini for LLM responses.

## Architecture Diagram

```mermaid
graph TD
    subgraph Data Layer
        Raw[Raw CSV Data]
        PG[(PostgreSQL + pgvector)]
    end

    subgraph ETL Pipeline
        Migrate[migrate_db.py / Airflow DAG]
        Gemini_Emb[Gemini Embedding API]
    end

    subgraph Core Logic
        RAG[RAG Engine]
        API_Logic[API Logic]
    end

    subgraph Interfaces
        Web[Web Chat Interface]
        API[FastAPI Server]
        Airflow[Airflow UI]
    end

    Raw --> Migrate
    Migrate --> PG
    Migrate --> Gemini_Emb
    Gemini_Emb --> PG

    PG --> API_Logic
    API_Logic --> API

    PG --> RAG
    RAG --> Web
    RAG --> API
```

## Data Lineage

The following UML diagram visualizes the data lineage from raw sources to the final user interfaces.

```mermaid
classDiagram
    class RawData {
        +Product_Information_Dataset.csv
        +Order_Data_Dataset.csv
    }

    class MigrateDB {
        +migrate_db.py
        +setup_database()
        +generate_embeddings()
        +insert_products()
        +insert_orders()
    }

    class PostgreSQL {
        +products table
        +orders table
        +chat_history table
        +vector(768) embeddings
    }

    class GeminiAPI {
        +embedding-001
        +gemini-2.5-flash-lite
    }

    class RAGSystem {
        +ECommerceRAG
        +semantic_search() via pgvector
        +get_customer_orders()
        +generate_llm_response()
    }

    class APIService {
        +FastAPI
        +search_products()
        +get_orders()
        +chat endpoint
    }

    class UserInterface {
        +Web Chat UI
        +REST API
        +Airflow DAGs
    }

    RawData ..> MigrateDB : Input
    MigrateDB ..> GeminiAPI : Generate embeddings
    MigrateDB ..> PostgreSQL : Store data + embeddings
    GeminiAPI ..> PostgreSQL : vector(768)
    PostgreSQL ..> RAGSystem : Query with pgvector
    GeminiAPI ..> RAGSystem : LLM responses
    RAGSystem ..> APIService : Process queries
    APIService ..> UserInterface : JSON/Chat Responses
```

## Component Details

### 1. Data Layer
*   **Raw Data**: Located in `data/raw/`, containing original CSV files for products and orders.
*   **PostgreSQL + pgvector**: All data stored in PostgreSQL with vector embeddings.
    *   `products` table: Product info + `embedding vector(768)`
    *   `orders` table: Order info + `embedding vector(768)`
    *   `chat_history` table: Conversation history

### 2. ETL Pipeline
*   **migrate_db.py**: Main script for data migration
    *   Loads raw CSV files
    *   Creates database schema with pgvector extension
    *   Generates embeddings via Google Gemini `embedding-001`
    *   Inserts data with embeddings into PostgreSQL
*   **Airflow DAGs** (optional):
    *   `embedding_pipeline_dag`: Scheduled embedding generation
    *   `data_ingestion_dag`: Daily data loading
    *   `maintenance_dag`: Weekly cleanup and health checks

### 3. RAG Engine (`src/rag/`)
*   **Core Logic**: Implemented in `assistant.py`.
*   **Functionality**:
    *   Performs **semantic search** using pgvector's cosine distance (`<=>` operator)
    *   Generates query embeddings via Gemini `embedding-001`
    *   Handles order queries by filtering PostgreSQL tables
    *   **Generates natural language responses** using Google Gemini LLM (gemini-2.5-flash-lite)
*   **LLM Integration**:
    *   Uses `google-generativeai` SDK to interact with Gemini
    *   Constructs prompts with user query and retrieved context
    *   Returns conversational, context-aware responses

### 4. API Service (`src/api/`)
*   **Framework**: FastAPI
*   **Endpoints**:
    *   `/api/chat`: Chat with RAG assistant
    *   `/api/products`: Product search and filtering
    *   `/api/orders`: Order queries by customer ID or priority
*   **Logic**: Queries PostgreSQL directly, uses pgvector for semantic search

### 5. Interfaces
*   **Web Chat UI**: Modern chat interface at `http://localhost:8000/static/index.html`
*   **Swagger UI**: Auto-generated API documentation at `http://localhost:8000/docs`
*   **Airflow UI**: DAG management at `http://localhost:8080` (admin/admin)
