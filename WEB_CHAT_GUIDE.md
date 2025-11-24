# Web Chat Interface Setup Guide

## Overview
The E-Commerce RAG Chatbot now includes a modern web-based chat interface with persistent chat history stored in PostgreSQL.

## Features
- 💬 Real-time chat interface
- 💾 Persistent chat history in PostgreSQL
- 🔄 Session management
- 👤 Customer ID tracking
- 📱 Responsive design
- 🎨 Modern UI/UX

## Setup Instructions

### 1. Create Chat History Table

First, run the migration script to create the chat history table:

```bash
python scripts/create_chat_history_table.py
```

This will create a `chat_history` table with the following schema:
- `id`: Primary key (auto-increment)
- `session_id`: Unique session identifier
- `customer_id`: Optional customer ID
- `user_message`: User's message
- `bot_response`: Bot's response
- `timestamp`: Message timestamp
- `metadata`: Additional metadata (JSON)

### 2. Start the API Server

Start the FastAPI server:

```bash
python scripts/run.py api
```

Or manually:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the Web Chat

Open your browser and navigate to:
```
http://localhost:8000/static/index.html
```

## Usage

### Basic Chat Commands

1. **Set Customer ID** (required for order-related queries):
   ```
   set customer 37077
   ```

2. **Product Search**:
   ```
   Show me laptops under $1000
   What are the best rated headphones?
   I need a wireless mouse
   ```

3. **Order Queries** (requires customer ID):
   ```
   Show my orders
   What's my last order?
   Show my order history
   ```

4. **General Queries**:
   ```
   What high priority orders do you have?
   Show me products with rating above 4.5
   ```

### Chat Features

- **Session Persistence**: Your chat session is saved and will persist across page refreshes
- **Customer ID Memory**: Once set, your customer ID is remembered in the browser
- **Clear Chat**: Use the 🗑️ button to clear chat history and start a new session
- **Auto-scroll**: Chat automatically scrolls to the latest message
- **Typing Indicator**: Shows when the bot is processing your message

## API Endpoints

### Chat Endpoints

#### 1. Send Message
```http
POST /chat/message
Content-Type: application/json

{
  "message": "Show me laptops",
  "session_id": "optional-session-id",
  "customer_id": "optional-customer-id"
}
```

Response:
```json
{
  "response": "Bot response here",
  "session_id": "session_abc123",
  "timestamp": "2025-11-25T10:30:00"
}
```

#### 2. Get Chat History by Session
```http
GET /chat/history/{session_id}?limit=50
```

Response:
```json
{
  "history": [
    {
      "id": 1,
      "session_id": "session_abc123",
      "customer_id": "37077",
      "user_message": "Show me laptops",
      "bot_response": "Here are some laptops...",
      "timestamp": "2025-11-25T10:30:00",
      "metadata": {"source": "web_chat"}
    }
  ]
}
```

#### 3. Get Chat History by Customer
```http
GET /chat/history/customer/{customer_id}?limit=100
```

#### 4. Delete Chat History
```http
DELETE /chat/history/{session_id}
```

## Architecture

```
┌─────────────┐
│   Browser   │
│  (Static    │
│   Files)    │
└──────┬──────┘
       │
       │ HTTP Requests
       │
┌──────▼──────┐
│  FastAPI    │
│   Server    │
│             │
│  /chat/*    │
└──────┬──────┘
       │
       ├─────────────┐
       │             │
┌──────▼──────┐  ┌──▼──────────┐
│    RAG      │  │  PostgreSQL │
│  Assistant  │  │   Database  │
│             │  │             │
│  - Gemini   │  │ - Products  │
│  - Semantic │  │ - Orders    │
│    Search   │  │ - Chat Hist │
└─────────────┘  └─────────────┘
```

## Database Schema

### chat_history Table
```sql
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    customer_id TEXT,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Indexes for performance
CREATE INDEX idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX idx_chat_history_customer_id ON chat_history(customer_id);
CREATE INDEX idx_chat_history_timestamp ON chat_history(timestamp);
```

## Customization

### Frontend Styling

Edit `/static/style.css` to customize:
- Colors and gradients
- Font sizes and families
- Layout and spacing
- Animations

### API Configuration

Edit `/src/config.py` to configure:
- Database connection
- API keys
- Server settings

### Chat Behavior

Edit `/src/rag/assistant.py` to modify:
- Response generation
- Query classification
- Semantic search logic

## Troubleshooting

### Chat Not Loading
1. Ensure API server is running on port 8000
2. Check browser console for errors
3. Verify static files are in `/static/` directory

### Messages Not Saving
1. Check database connection in `.env`
2. Verify chat_history table exists
3. Check API server logs for errors

### CORS Issues
If accessing from a different domain, update CORS settings in `/src/api/main.py`

## Production Deployment

For production deployment:

1. **Use HTTPS**: Configure SSL certificates
2. **Set CORS**: Restrict allowed origins
3. **Environment Variables**: Use production database credentials
4. **Static Files**: Consider using a CDN
5. **Rate Limiting**: Add rate limiting middleware
6. **Authentication**: Implement user authentication if needed

Example production CORS config:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

## Future Enhancements

Potential improvements:
- [ ] User authentication and authorization
- [ ] Multi-user support with user accounts
- [ ] File upload for product images
- [ ] Voice input/output
- [ ] Chat export functionality
- [ ] Advanced analytics dashboard
- [ ] WebSocket for real-time updates
- [ ] Mobile app integration
