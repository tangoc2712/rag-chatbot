# RAG Chatbot API Documentation

This document provides comprehensive API documentation for integrating the E-Commerce RAG Chatbot into external systems.

## Table of Contents

1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication & User Scenarios](#authentication--user-scenarios)
4. [API Endpoints](#api-endpoints)
5. [Integration Examples](#integration-examples)
6. [Error Handling](#error-handling)
7. [Environment Setup](#environment-setup)

---

## Overview

The RAG Chatbot API provides a conversational interface for e-commerce data. It uses semantic search with pgvector and Google Gemini LLM to provide intelligent, context-aware responses.

### Key Features
- 🤖 AI-powered conversational responses
- 🔍 Semantic search across products, orders, reviews, and more
- 👥 Role-based access control (Visitor, User, Admin)
- 💬 Session-based conversation history
- 📝 Automatic chat history persistence

---

## Base URL

```
http://localhost:8000
```

For production, replace with your deployed server URL.

### Available Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI documentation |
| `POST` | `/chat/message` | Send a chat message |
| `GET` | `/chat/history/{session_id}` | Get session chat history |
| `GET` | `/chat/history/customer/{customer_id}` | Get customer chat history |
| `DELETE` | `/chat/history/{session_id}` | Delete session chat history |

---

## Authentication & User Scenarios

The chatbot operates in **three different scenarios** based on the `customer_id` provided:

### Scenario 1: Visitor (No Account)

**When to use:** For anonymous users browsing your website who haven't logged in.

**Access Level:**
- ✅ Products (names, descriptions, prices, stock, colors, sizes, materials)
- ✅ Product reviews and ratings
- ✅ Product categories
- ❌ Orders, payments, shipping (encouraged to sign up)
- ❌ User account information

**Request:**
```json
{
    "message": "Show me popular products",
    "session_id": "optional-session-id"
    // No customer_id = Visitor mode
}
```

---

### Scenario 2: Regular User (Logged In)

**When to use:** For authenticated users with a standard user account.

**Access Level:**
- ✅ All visitor permissions
- ✅ Their own orders (status, items, history)
- ✅ Their own shipments and tracking
- ❌ Other users' data
- ❌ Admin-level analytics

**Request:**
```json
{
    "message": "Where is my order?",
    "session_id": "optional-session-id",
    "customer_id": "user-uid-or-user-id"
}
```

---

### Scenario 3: Admin (Full Access)

**When to use:** For administrators with full database access.

**Access Level:**
- ✅ All products and inventory
- ✅ All orders and order items
- ✅ All users and customer data
- ✅ All payments and transactions
- ✅ All shipments and tracking
- ✅ All reviews and ratings
- ✅ All coupons and discounts
- ✅ All carts and cart items
- ✅ All events and analytics

**Request:**
```json
{
    "message": "Show me total revenue this month",
    "session_id": "optional-session-id",
    "customer_id": "admin-uid-or-user-id"
}
```

**Note:** The user's role is determined by looking up the `customer_id` in the database. Users with `role = 'admin'` get full access.

---

## API Endpoints

### 1. Send Chat Message

**Endpoint:** `POST /chat/message`

**Description:** Send a message to the chatbot and receive an AI-generated response.

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
    "message": "string (required)",
    "session_id": "string (optional)",
    "customer_id": "string (optional)"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | The user's question or message |
| `session_id` | string | No | Session ID for conversation continuity. Auto-generated if not provided. |
| `customer_id` | string | No | User's ID (`uid` or `user_id`). Omit for visitor mode. |

#### Response

**Success (200 OK):**
```json
{
    "response": "string - The AI-generated response",
    "session_id": "string - The session ID (use for follow-up messages)",
    "timestamp": "string - ISO 8601 timestamp",
    "debug_info": {
        "query_type": "visitor_query | user_query | admin_query",
        "is_intro": false,
        "user_role": "visitor | user | admin",
        "data_accessed": ["products", "reviews", ...],
        "search_results_count": 5
    }
}
```

#### Example: Visitor Query

**Request:**
```bash
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the best rated products"
  }'
```

**Response:**
```json
{
    "response": "Hey there! 🎉 Looking for the cream of the crop? Here are our top-rated products...",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-12-04T10:30:00.000000",
    "debug_info": {
        "query_type": "visitor_query",
        "is_intro": false,
        "user_role": "visitor",
        "data_accessed": ["products", "reviews"],
        "search_results_count": 8
    }
}
```

#### Example: User Query

**Request:**
```bash
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the status of my recent orders?",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_id": "user123"
  }'
```

**Response:**
```json
{
    "response": "Hey there, valued customer! 🌟 Let me check on your orders...",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-12-04T10:31:00.000000",
    "debug_info": {
        "query_type": "user_query",
        "user_id": "user123",
        "is_intro": false,
        "user_role": "user",
        "data_accessed": ["user_orders", "user_shipments"],
        "search_results_count": 3
    }
}
```

#### Example: Admin Query

**Request:**
```bash
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many orders do we have this month?",
    "customer_id": "admin-user-id"
  }'
```

**Response:**
```json
{
    "response": "Great question! 📊 Let me pull up those order statistics for you...",
    "session_id": "660e8400-e29b-41d4-a716-446655440001",
    "timestamp": "2025-12-04T10:32:00.000000",
    "debug_info": {
        "query_type": "admin_query",
        "is_intro": false,
        "user_role": "admin",
        "data_accessed": ["orders"],
        "search_results_count": 10
    }
}
```

---

### 2. Get Chat History by Session

**Endpoint:** `GET /chat/history/{session_id}`

**Description:** Retrieve the conversation history for a specific session.

#### Request

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | The session ID |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Maximum number of messages to return |

#### Response

**Success (200 OK):**
```json
{
    "history": [
        {
            "id": 1,
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "customer_id": "user123",
            "user_message": "What products do you have?",
            "bot_response": "We have a great selection of products...",
            "timestamp": "2025-12-04T10:30:00.000000",
            "metadata": {
                "source": "web_chat",
                "role": "user",
                "debug": {...}
            }
        }
    ]
}
```

#### Example

```bash
curl -X GET "http://localhost:8000/chat/history/550e8400-e29b-41d4-a716-446655440000?limit=20"
```

---

### 3. Get Chat History by Customer

**Endpoint:** `GET /chat/history/customer/{customer_id}`

**Description:** Retrieve all conversation history for a specific customer across all sessions.

#### Request

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `customer_id` | string | The customer's ID |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 100 | Maximum number of messages to return |

#### Response

**Success (200 OK):**
```json
{
    "history": [
        {
            "id": 5,
            "session_id": "session-2",
            "customer_id": "user123",
            "user_message": "Track my order",
            "bot_response": "Your order is on its way...",
            "timestamp": "2025-12-04T11:00:00.000000",
            "metadata": {...}
        },
        {
            "id": 1,
            "session_id": "session-1",
            "customer_id": "user123",
            "user_message": "Show me products",
            "bot_response": "Here are some great products...",
            "timestamp": "2025-12-04T10:00:00.000000",
            "metadata": {...}
        }
    ]
}
```

#### Example

```bash
curl -X GET "http://localhost:8000/chat/history/customer/user123?limit=50"
```

---

### 4. Delete Chat History

**Endpoint:** `DELETE /chat/history/{session_id}`

**Description:** Delete all conversation history for a specific session.

#### Request

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | The session ID to delete |

#### Response

**Success (200 OK):**
```json
{
    "message": "Chat history deleted for session 550e8400-e29b-41d4-a716-446655440000"
}
```

#### Example

```bash
curl -X DELETE "http://localhost:8000/chat/history/550e8400-e29b-41d4-a716-446655440000"
```

---

### 5. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running.

#### Response

**Success (200 OK):**
```json
{
    "status": "healthy"
}
```

---

### 6. API Information

**Endpoint:** `GET /`

**Description:** Get basic API information.

#### Response

**Success (200 OK):**
```json
{
    "name": "E-commerce Dataset API",
    "version": "1.0.0",
    "documentation": "/docs",
    "health_check": "/health",
    "chat_interface": "/static/index.html"
}
```

---

## Integration Examples

### JavaScript/TypeScript

```javascript
class ChatbotClient {
    constructor(baseUrl, customerId = null) {
        this.baseUrl = baseUrl;
        this.customerId = customerId;
        this.sessionId = null;
    }

    async sendMessage(message) {
        const response = await fetch(`${this.baseUrl}/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId,
                customer_id: this.customerId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        this.sessionId = data.session_id; // Store for conversation continuity
        return data;
    }

    async getHistory() {
        if (!this.sessionId) return { history: [] };
        
        const response = await fetch(
            `${this.baseUrl}/chat/history/${this.sessionId}`
        );
        return response.json();
    }
}

// Usage Examples:

// Visitor mode
const visitorChat = new ChatbotClient('http://localhost:8000');
const response1 = await visitorChat.sendMessage('Show me popular products');

// User mode
const userChat = new ChatbotClient('http://localhost:8000', 'user-123');
const response2 = await userChat.sendMessage('Where is my order?');

// Admin mode
const adminChat = new ChatbotClient('http://localhost:8000', 'admin-user-id');
const response3 = await adminChat.sendMessage('Show total revenue');
```

### Python

```python
import requests
from typing import Optional

class ChatbotClient:
    def __init__(self, base_url: str, customer_id: Optional[str] = None):
        self.base_url = base_url
        self.customer_id = customer_id
        self.session_id = None

    def send_message(self, message: str) -> dict:
        payload = {
            "message": message,
            "session_id": self.session_id,
            "customer_id": self.customer_id
        }
        
        response = requests.post(
            f"{self.base_url}/chat/message",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        self.session_id = data["session_id"]
        return data

    def get_history(self, limit: int = 50) -> dict:
        if not self.session_id:
            return {"history": []}
        
        response = requests.get(
            f"{self.base_url}/chat/history/{self.session_id}",
            params={"limit": limit}
        )
        return response.json()

    def clear_history(self) -> dict:
        if not self.session_id:
            return {"message": "No session to clear"}
        
        response = requests.delete(
            f"{self.base_url}/chat/history/{self.session_id}"
        )
        return response.json()


# Usage Examples:

# Visitor mode
visitor_chat = ChatbotClient("http://localhost:8000")
response = visitor_chat.send_message("What products do you have?")
print(response["response"])

# User mode
user_chat = ChatbotClient("http://localhost:8000", customer_id="user-123")
response = user_chat.send_message("Track my recent order")
print(response["response"])

# Admin mode
admin_chat = ChatbotClient("http://localhost:8000", customer_id="admin-id")
response = admin_chat.send_message("Show me order analytics")
print(response["response"])
```

### React Integration

```jsx
import React, { useState, useEffect } from 'react';

function ChatWidget({ customerId }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);

    const sendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setLoading(true);

        try {
            const response = await fetch('http://localhost:8000/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMessage,
                    session_id: sessionId,
                    customer_id: customerId // null for visitors
                })
            });

            const data = await response.json();
            setSessionId(data.session_id);
            setMessages(prev => [...prev, { role: 'bot', content: data.response }]);
        } catch (error) {
            setMessages(prev => [...prev, { 
                role: 'bot', 
                content: 'Sorry, something went wrong.' 
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-widget">
            <div className="messages">
                {messages.map((msg, i) => (
                    <div key={i} className={`message ${msg.role}`}>
                        {msg.content}
                    </div>
                ))}
                {loading && <div className="typing">...</div>}
            </div>
            <form onSubmit={sendMessage}>
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask something..."
                />
                <button type="submit">Send</button>
            </form>
        </div>
    );
}

// Usage:
// <ChatWidget /> - Visitor mode
// <ChatWidget customerId="user-123" /> - Logged-in user
// <ChatWidget customerId="admin-id" /> - Admin user
```

### cURL Examples

```bash
# Visitor: Ask about products
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me trending products"}'

# User: Track order (with customer_id)
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Where is my order?",
    "customer_id": "user-123",
    "session_id": "existing-session-id"
  }'

# Admin: Get analytics
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me total orders and revenue",
    "customer_id": "admin-user-id"
  }'

# Get chat history
curl -X GET "http://localhost:8000/chat/history/session-id-here"

# Delete chat history
curl -X DELETE "http://localhost:8000/chat/history/session-id-here"
```

---

## Error Handling

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

### Error Response Format

```json
{
    "detail": "Error message describing what went wrong"
}
```

### Common Errors

**Invalid request body:**
```json
{
    "detail": [
        {
            "loc": ["body", "message"],
            "msg": "field required",
            "type": "value_error.missing"
        }
    ]
}
```

**Session not found:**
```json
{
    "detail": "Session not found"
}
```

**Server error:**
```json
{
    "detail": "Internal server error message"
}
```

---

## Environment Setup

### Required Environment Variables

Create a `.env` file in the project root:

```env
# API Settings
HOST=0.0.0.0
PORT=8000

# Database Settings
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=ecommerce_rag

# Google API Key (required for LLM and embeddings)
GOOGLE_API_KEY=your_google_api_key

# Development
DEBUG=true
RELOAD=true
```

### Running the API

```bash
# Using the run script
python scripts/run.py api

# Or with options
python scripts/run.py api --host 0.0.0.0 --port 8000 --reload

# Or directly with uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Deployment

```bash
# Start with docker-compose
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

---

## Data Access by Role

| Data Type | Visitor | User | Admin |
|-----------|---------|------|-------|
| Products | ✅ | ✅ | ✅ |
| Product Reviews | ✅ | ✅ | ✅ |
| Categories | ✅ | ✅ | ✅ |
| Own Orders | ❌ | ✅ | ✅ |
| Own Shipments | ❌ | ✅ | ✅ |
| All Orders | ❌ | ❌ | ✅ |
| All Users | ❌ | ❌ | ✅ |
| All Payments | ❌ | ❌ | ✅ |
| All Shipments | ❌ | ❌ | ✅ |
| Inventory | ❌ | ❌ | ✅ |
| Coupons | ❌ | ❌ | ✅ |
| Carts | ❌ | ❌ | ✅ |
| Events/Analytics | ❌ | ❌ | ✅ |

---

## Best Practices

1. **Session Management:** Store and reuse `session_id` for conversation continuity
2. **Customer ID:** Always pass `customer_id` for authenticated users to enable personalized responses
3. **Error Handling:** Implement proper error handling for network failures and API errors
4. **Rate Limiting:** Consider implementing client-side rate limiting for production use
5. **Caching:** Cache static responses where appropriate
6. **Security:** Never expose admin customer IDs to regular users

---

## Support

- **API Documentation (Swagger):** `http://localhost:8000/docs`
- **Interactive API (ReDoc):** `http://localhost:8000/redoc`
- **Health Check:** `http://localhost:8000/health`
