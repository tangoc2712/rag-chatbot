# RAG Service API Guide

Complete API documentation for the E-commerce RAG Service.

---

## 📋 Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [Visitor Chat](#visitor-chat)
  - [User Chat](#user-chat)
  - [Admin Chat](#admin-chat)
- [Request/Response Formats](#requestresponse-formats)
- [Role-Based Access](#role-based-access)
- [Error Handling](#error-handling)
- [Code Examples](#code-examples)

---

## Base URL

**Production (Internal Only):**
```
https://rag-service-359180589188.asia-southeast1.run.app
```

**Access:** Internal Cloud Run services only (same GCP project)

---

## Authentication

**Current Setup:** No authentication required

**Security:** 
- Service uses **internal ingress** - only accessible from other Cloud Run services in `hackathon-478514` project
- Not accessible from public internet
- Backend service (`hackathon-ecom-server`) acts as gateway with authentication

---

## Endpoints

### Health Check

Check if the service is running and healthy.

**Endpoint:** `GET /health`

**Request:**
```bash
curl https://rag-service-359180589188.asia-southeast1.run.app/health
```

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is down

---

### Chat Message

**Endpoint:** `POST /chat/message`

Single unified endpoint that automatically routes to visitor/user/admin mode based on `customer_id` and database role lookup.

#### Scenario 1: Visitor Mode (No customer_id)

General product queries for anonymous/public users. Access to products and reviews only.

**Request Body:**
```json
{
  "message": "What products do you sell?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "response": "We offer a wide range of products including laptops, smartphones, tablets, and accessories. Our top categories are electronics, computers, and mobile devices. Would you like to know about any specific product category?",
  "session_id": "abc-123-def",
  "timestamp": "2024-12-04T10:30:00",
  "debug_info": {
    "user_role": "visitor"
  }
}
```

**Example Use Cases:**
- "What products do you have?"
- "Show me laptops under $1000"
- "What are your best-rated headphones?"
- "Do you sell gaming accessories?"

---

#### Scenario 2: User Mode (customer_id with role='user')

Personalized queries for authenticated users. Access to their own orders + products/reviews.

**Request Body:**
```json
{
  "message": "Show me my recent orders",
  "session_id": "optional-session-id",
  "customer_id": "USER123"
}
```

**Response:**
```json
{
  "response": "Here are your recent orders:\n\n1. Order #ORD-2024-001 - $1,299.99 - Delivered on Dec 1, 2024\n   - MacBook Pro 14\" \n\n2. Order #ORD-2024-002 - $299.99 - In Transit\n   - Sony WH-1000XM5 Headphones\n\nWould you like details about any specific order?",
  "session_id": "abc-123-def",
  "timestamp": "2024-12-04T10:30:00",
  "debug_info": {
    "user_role": "user"
  }
}
```

**Example Use Cases:**
- "Show me my order history"
- "Where is my order #ORD-2024-002?"
- "What did I buy last month?"
- "Recommend products based on my purchases"
- "Products I might like"

---

#### Scenario 3: Admin Mode (customer_id with role='admin')

Analytics and business intelligence queries. Full database access for reporting.

**Request Body:**
```json
{
  "message": "What are the top 5 selling products this month?",
  "session_id": "optional-session-id",
  "customer_id": "ADMIN_USER"
}
```

**Response:**
```json
{
  "response": "Top 5 Selling Products (December 2024):\n\n1. iPhone 15 Pro - 127 units sold - $152,873 revenue\n2. MacBook Air M3 - 89 units sold - $106,800 revenue\n3. Sony WH-1000XM5 - 156 units sold - $46,800 revenue\n4. Samsung Galaxy S24 - 98 units sold - $88,200 revenue\n5. AirPods Pro 2 - 203 units sold - $50,750 revenue\n\nTotal Revenue: $445,423",
  "session_id": "abc-123-def",
  "timestamp": "2024-12-04T10:30:00",
  "debug_info": {
    "user_role": "admin"
  }
}
```

**Example Use Cases:**
- "What's our total revenue this month?"
- "Top 10 customers by spending"
- "Average order value this week"
- "Products with low inventory"
- "Sales trends for last quarter"
- "Customer churn rate"

---

### Chat History (By Session)

Get chat history for a specific session.

**Endpoint:** `GET /chat/history/{session_id}`

**Query Parameters:**
- `limit` (optional, default=50): Maximum number of messages to return

**Request:**
```bash
curl https://rag-service-359180589188.asia-southeast1.run.app/chat/history/abc-123-def?limit=50
```

**Response:**
```json
{
  "history": [
    {
      "id": 1,
      "session_id": "abc-123-def",
      "customer_id": "USER123",
      "user_message": "Show me my recent orders",
      "bot_response": "Here are your recent orders...",
      "timestamp": "2024-12-04T10:30:00",
      "metadata": {
        "source": "web_chat",
        "role": "user"
      }
    }
  ]
}
```

---

### Chat History (By Customer)

Get all chat history for a specific customer across all sessions.

**Endpoint:** `GET /chat/history/customer/{customer_id}`

**Query Parameters:**
- `limit` (optional, default=100): Maximum number of messages to return

**Request:**
```bash
curl https://rag-service-359180589188.asia-southeast1.run.app/chat/history/customer/USER123?limit=100
```

**Response:**
```json
{
  "history": [
    {
      "id": 1,
      "session_id": "abc-123-def",
      "customer_id": "USER123",
      "user_message": "Show me my recent orders",
      "bot_response": "Here are your recent orders...",
      "timestamp": "2024-12-04T10:30:00",
      "metadata": {
        "source": "web_chat",
        "role": "user"
      }
    }
  ]
}
```

---

### Delete Chat History

Delete chat history for a specific session.

**Endpoint:** `DELETE /chat/history/{session_id}`

**Request:**
```bash
curl -X DELETE https://rag-service-359180589188.asia-southeast1.run.app/chat/history/abc-123-def
```

**Response:**
```json
{
  "message": "Chat history deleted for session abc-123-def"
}
```

---

## Request/Response Formats

### Request Schema

**Chat Message Endpoint:**

```json
{
  "message": "string (required) - User's question or query",
  "session_id": "string (optional) - Session identifier for conversation tracking",
  "customer_id": "string (optional) - User ID (determines visitor/user/admin mode)"
}
```

**Field Details:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ Yes | User's natural language query |
| `session_id` | string | ❌ No | Session identifier (auto-generated if not provided) |
| `customer_id` | string | ❌ No | User ID - omit for visitor mode, provide for user/admin mode |

**How customer_id determines mode:**
- **No customer_id**: Visitor mode (products + reviews only)
- **customer_id with role='user' in DB**: User mode (own orders + products/reviews)
- **customer_id with role='admin' in DB**: Admin mode (full access)

### Response Schema

**Chat Message Response:**

```json
{
  "response": "string - AI-generated response",
  "session_id": "string - Session identifier",
  "timestamp": "string - ISO 8601 timestamp",
  "debug_info": {
    "user_role": "string - Role used (visitor/user/admin)",
    ...
  }
}
```

**Field Details:**

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Natural language answer from RAG system |
| `session_id` | string | Session ID for conversation tracking |
| `timestamp` | string | ISO 8601 formatted timestamp |
| `debug_info` | object | Debug information including user role and query details |

**Chat History Response:**

```json
{
  "history": [
    {
      "id": "integer - Message ID",
      "session_id": "string - Session identifier",
      "customer_id": "string - Customer UUID or null",
      "user_message": "string - User's message",
      "bot_response": "string - Bot's response",
      "timestamp": "string - ISO 8601 timestamp",
      "metadata": "object - Additional metadata"
    }
  ]
}
```

---

## Role-Based Access

### How Role Detection Works

The API uses a **single endpoint** (`/chat/message`) that automatically determines the user's role:

1. **No `customer_id`** → Visitor mode
2. **`customer_id` provided** → Query database `user` table for role:
   - If `role='admin'` → Admin mode
   - If `role='user'` → User mode
   - If not found → Defaults to visitor mode

### Access Matrix

| Role | Products | Reviews | User Orders | All Orders | Analytics |
|------|----------|---------|-------------|------------|-----------|
| **Visitor** | ✅ Read | ✅ Read | ❌ No | ❌ No | ❌ No |
| **User** | ✅ Read | ✅ Read | ✅ Own Only | ❌ No | ❌ No |
| **Admin** | ✅ Read | ✅ Read | ✅ All | ✅ All | ✅ Full |

### Implementation Guide

**For Visitor (anonymous user):**
```json
{
  "message": "What products do you sell?"
}
```

**For User (authenticated, non-admin):**
```json
{
  "message": "Show me my orders",
  "customer_id": "user-uid-from-auth"
}
```

**For Admin:**
```json
{
  "message": "Total revenue this month",
  "customer_id": "admin-uid-from-auth"
}
```

The API automatically looks up the role from the database and routes to the appropriate assistant.

---

## Error Handling

### HTTP Status Codes

| Code | Description | Reason |
|------|-------------|--------|
| `200 OK` | Success | Request processed successfully |
| `400 Bad Request` | Invalid input | Malformed JSON or missing required fields |
| `404 Not Found` | Endpoint not found | Invalid URL path |
| `422 Unprocessable Entity` | Validation error | Field validation failed |
| `500 Internal Server Error` | Server error | Database or AI service failure |
| `503 Service Unavailable` | Service down | Health check failed |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**1. Missing Message Field**
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

**2. Empty Message**
```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "ensure this value has at least 1 character",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**3. Database Connection Error**
```json
{
  "detail": "Database connection failed. Please try again later."
}
```

---

## Code Examples

### Python (requests)

```python
import requests

BASE_URL = "https://rag-service-359180589188.asia-southeast1.run.app"

# Visitor query (no customer_id)
response = requests.post(
    f"{BASE_URL}/chat/message",
    json={"message": "What products do you sell?"},
    timeout=30
)
data = response.json()
print(data["response"])
print(f"Role: {data['debug_info']['user_role']}")

# User query (with customer_id)
response = requests.post(
    f"{BASE_URL}/chat/message",
    json={
        "message": "Show me my orders",
        "customer_id": "USER123"
    },
    timeout=30
)
data = response.json()
print(data["response"])

# Admin query (admin customer_id in database)
response = requests.post(
    f"{BASE_URL}/chat/message",
    json={
        "message": "Total revenue this month",
        "customer_id": "ADMIN_USER"
    },
    timeout=30
)
data = response.json()
print(data["response"])
```

### Python (httpx - async)

```python
import httpx
import asyncio

async def chat_with_rag(message: str, customer_id: str = None):
    async with httpx.AsyncClient() as client:
        payload = {"message": message}
        if customer_id:
            payload["customer_id"] = customer_id
            
        response = await client.post(
            "https://rag-service-359180589188.asia-southeast1.run.app/chat/message",
            json=payload,
            timeout=30.0
        )
        return response.json()

# Usage
# Visitor
result = asyncio.run(chat_with_rag("Show me laptops"))
print(result["response"])

# User
result = asyncio.run(chat_with_rag("My orders", customer_id="USER123"))
print(result["response"])
```

### Node.js (fetch)

```javascript
const fetch = require('node-fetch');

async function chatWithRAG(message, customerId = null) {
  const payload = { message };
  if (customerId) {
    payload.customer_id = customerId;
  }
  
  const response = await fetch(
    'https://rag-service-359180589188.asia-southeast1.run.app/chat/message',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  );
  
  const data = await response.json();
  return data;
}

// Usage
// Visitor
chatWithRAG('What are your best products?')
  .then(data => {
    console.log(data.response);
    console.log('Role:', data.debug_info.user_role);
  });

// User  
chatWithRAG('Show my orders', 'USER123')
  .then(data => console.log(data.response));
```

### cURL

```bash
# Visitor chat (no customer_id)
curl -X POST "https://rag-service-359180589188.asia-southeast1.run.app/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "What products do you have?"}'

# User chat (with customer_id)
curl -X POST "https://rag-service-359180589188.asia-southeast1.run.app/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show my orders",
    "customer_id": "USER123",
    "session_id": "abc-123-def"
  }'

# Admin query
curl -X POST "https://rag-service-359180589188.asia-southeast1.run.app/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Total revenue this month?",
    "customer_id": "ADMIN_USER"
  }'

# Get chat history
curl "https://rag-service-359180589188.asia-southeast1.run.app/chat/history/abc-123-def?limit=50"

# Get customer chat history
curl "https://rag-service-359180589188.asia-southeast1.run.app/chat/history/customer/USER123?limit=100"

# Delete chat history
curl -X DELETE "https://rag-service-359180589188.asia-southeast1.run.app/chat/history/abc-123-def"
```

### Java (Spring WebClient)

```java
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import java.util.HashMap;
import java.util.Map;

public class RAGClient {
    
    private final WebClient webClient;
    
    public RAGClient() {
        this.webClient = WebClient.builder()
            .baseUrl("https://rag-service-359180589188.asia-southeast1.run.app")
            .build();
    }
    
    public Mono<Map> chat(String message, String customerId) {
        Map<String, String> request = new HashMap<>();
        request.put("message", message);
        if (customerId != null) {
            request.put("customer_id", customerId);
        }
        
        return webClient.post()
            .uri("/chat/message")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(Map.class);
    }
}

// Usage
RAGClient client = new RAGClient();

// Visitor
Map response = client.chat("What products do you sell?", null).block();
System.out.println(response.get("response"));

// User
Map userResponse = client.chat("My orders", "USER123").block();
System.out.println(userResponse.get("response"));
```

### Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
)

type ChatRequest struct {
    Message    string  `json:"message"`
    CustomerID *string `json:"customer_id,omitempty"`
    SessionID  *string `json:"session_id,omitempty"`
}

type ChatResponse struct {
    Response  string                 `json:"response"`
    SessionID string                 `json:"session_id"`
    Timestamp string                 `json:"timestamp"`
    DebugInfo map[string]interface{} `json:"debug_info"`
}

func chatWithRAG(message string, customerID *string) (*ChatResponse, error) {
    url := "https://rag-service-359180589188.asia-southeast1.run.app/chat/message"
    
    reqBody, _ := json.Marshal(ChatRequest{
        Message:    message,
        CustomerID: customerID,
    })
    
    resp, err := http.Post(url, "application/json", bytes.NewBuffer(reqBody))
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    body, _ := io.ReadAll(resp.Body)
    
    var chatResp ChatResponse
    json.Unmarshal(body, &chatResp)
    
    return &chatResp, nil
}

func main() {
    // Visitor
    response, _ := chatWithRAG("What products do you have?", nil)
    fmt.Println(response.Response)
    fmt.Println("Role:", response.DebugInfo["user_role"])
    
    // User
    userID := "USER123"
    userResponse, _ := chatWithRAG("Show my orders", &userID)
    fmt.Println(userResponse.Response)
}
```

---

## Testing & Development

### Health Check Test

```bash
# Should return {"status": "healthy"}
curl https://rag-service-359180589188.asia-southeast1.run.app/health
```

### Quick Test Script (Python)

```python
#!/usr/bin/env python3
import requests

BASE_URL = "https://rag-service-359180589188.asia-southeast1.run.app"

def test_chat(message, customer_id=None, label=""):
    print(f"\n{'='*60}")
    print(f"Testing: {label}")
    print(f"Question: {message}")
    if customer_id:
        print(f"Customer ID: {customer_id}")
    print(f"{'='*60}")
    
    payload = {"message": message}
    if customer_id:
        payload["customer_id"] = customer_id
    
    response = requests.post(
        f"{BASE_URL}/chat/message",
        json=payload,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"Role: {data['debug_info']['user_role']}")
        print(f"Response: {data['response']}")
        print(f"Session ID: {data['session_id']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Details: {response.text}")

# Run tests
test_chat("What products do you sell?", label="Visitor Mode")
test_chat("Show me my recent orders", customer_id="USER123", label="User Mode")
test_chat("What are the top 5 selling products?", customer_id="ADMIN_USER", label="Admin Mode")

# Test chat history
print(f"\n{'='*60}")
print("Testing: Get Chat History")
print(f"{'='*60}")
response = requests.get(f"{BASE_URL}/chat/history/customer/USER123?limit=10")
if response.status_code == 200:
    data = response.json()
    print(f"✅ Found {len(data['history'])} messages")
else:
    print(f"❌ Error: {response.status_code}")
```

---

## Rate Limits & Performance

**Current Configuration:**
- Max instances: 10
- Memory: 2 GiB per instance
- CPU: 2 vCPU per instance
- Timeout: 300 seconds (5 minutes)
- Min instances: 0 (scales to zero when idle)

**Expected Performance:**
- Cold start: ~3-5 seconds (first request after idle)
- Warm response: 200ms - 2 seconds
- Concurrent requests: Up to 10 instances × 80 requests/instance = 800 concurrent

**No hard rate limits** currently enforced. Implement in backend service if needed.

---

## Database Schema

The RAG service queries these tables:

- `products` - Product catalog
- `product_reviews` - Customer reviews
- `orders` - Order records
- `order_items` - Order line items
- `users` - Customer data
- `chat_history` - Conversation logs

**See:** `services/rag-service/src/database_schema.md` for full schema details.

---

## Monitoring & Logs

### View Live Logs

```bash
gcloud run services logs tail rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1
```

### View Recent Errors

```bash
gcloud run services logs read rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1 \
  --limit=100 \
  | grep ERROR
```

### Service Metrics

View in Google Cloud Console:
```
https://console.cloud.google.com/run/detail/asia-southeast1/rag-service/metrics?project=hackathon-478514
```

---

## Support & Troubleshooting

### Common Issues

**1. "Connection refused" or timeouts**
- ✅ Ensure calling from another Cloud Run service (internal ingress)
- ✅ Verify both services in same project (`hackathon-478514`)
- ✅ Check service is running: `gcloud run services describe rag-service`

**2. "404 Not Found"**
- ✅ Verify endpoint path: `/chat/message` (NOT `/chat/visitor`, `/chat/user`, or `/chat/admin`)
- ✅ Check HTTP method: Must be POST (not GET)

**3. Empty or generic responses**
- ✅ Check database has data
- ✅ Verify GOOGLE_API_KEY is set correctly
- ✅ Review logs for errors

**4. Wrong role detected**
- ✅ Verify `customer_id` exists in database `user` table
- ✅ Check `role` field in user record is set correctly ('user' or 'admin')
- ✅ If no `customer_id` provided, defaults to visitor mode

**5. Slow responses**
- ✅ Cold start expected on first request
- ✅ Consider setting min-instances > 0 for production
- ✅ Check database query performance

### Get Help

- **Logs:** `gcloud run services logs read rag-service`
- **Status:** `gcloud run services describe rag-service`
- **GCP Console:** https://console.cloud.google.com/run

---

## Changelog

### v1.0.0 (2025-12-04)
- ✅ Initial deployment
- ✅ Three role-based endpoints (visitor, user, admin)
- ✅ Internal ingress security
- ✅ PostgreSQL + pgvector integration
- ✅ Google Gemini AI integration
- ✅ Session tracking support

---

**🚀 Happy Building!**

For backend integration guide, see: `BACKEND_INTEGRATION.md`
