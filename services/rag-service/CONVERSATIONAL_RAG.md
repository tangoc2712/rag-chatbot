# Conversational RAG Implementation

## Overview

This implementation adds **conversational query rewriting** to the RAG chatbot, enabling natural multi-turn conversations by transforming follow-up questions into standalone queries before vector search retrieval.

## Problem Statement

### Before Implementation
The RAG system treated each query independently without conversational context:

```
User: "Show me red dresses"
Bot: [Shows red dresses successfully]

User: "What about in size medium?"
Bot: ❌ Doesn't understand "what about" refers to red dresses
     ❌ Vector search fails because "size medium" lacks context
```

### After Implementation
The system now maintains conversational context and rewrites queries:

```
User: "Show me red dresses"
Bot: [Shows red dresses successfully]

User: "What about in size medium?"
System: Rewrites to → "Show me red dresses in size medium"
Bot: ✅ Correctly retrieves medium-sized red dresses
```

## Architecture

### Query Processing Pipeline

```
1. User Query Received
   ↓
2. Retrieve Conversation History (last 5 messages from chat_history table)
   ↓
3. Query Rewriting (if history exists)
   - Send to Gemini: history + current query
   - Prompt: "Rewrite this follow-up into a standalone query"
   - Result: Context-independent query
   ↓
4. Semantic Search (using rewritten query)
   - Generate embedding for rewritten query
   - Search vector database with pgvector
   - Retrieve relevant documents
   ↓
5. Response Generation (using original query)
   - Context: Retrieved documents
   - Conversation: Original user query
   - Generate natural response
   ↓
6. Save to Database
   - Store both user message and bot response
   - Include metadata with rewritten query
```

## Key Components

### 1. Conversation History Retrieval (`utils.py`)

```python
def get_conversation_history(session_id: str, limit: int = 5) -> List[Dict[str, str]]
```

**Purpose**: Fetch recent conversation turns from the database

**Parameters**:
- `session_id`: Session identifier to retrieve history for
- `limit`: Maximum number of message pairs (default: 5)

**Returns**: List of dictionaries with `user_message`, `bot_response`, `timestamp`

**Example**:
```python
history = get_conversation_history("abc-123", limit=3)
# Returns:
# [
#   {"user_message": "Show me laptops", "bot_response": "Here are our laptops..."},
#   {"user_message": "Under $1000", "bot_response": "Budget laptops..."},
#   {"user_message": "With SSD", "bot_response": "SSD laptops..."}
# ]
```

### 2. Query Rewriting Service (`utils.py`)

```python
def rewrite_query_with_context(
    current_query: str, 
    conversation_history: List[Dict[str, str]],
    max_retries: int = 2
) -> str
```

**Purpose**: Transform follow-up queries into standalone questions using LLM

**Parameters**:
- `current_query`: The current user query (may contain references)
- `conversation_history`: Previous conversation turns
- `max_retries`: Number of retry attempts if LLM fails

**Returns**: Rewritten standalone query

**Example Transformations**:
```python
# Example 1: Pronoun resolution
history = [{"user_message": "Show me red shoes", "bot_response": "..."}]
rewrite_query_with_context("How much are they?", history)
# → "What is the price of red shoes?"

# Example 2: Implicit reference
history = [{"user_message": "Laptops with 16GB RAM", "bot_response": "..."}]
rewrite_query_with_context("Which ones have SSD?", history)
# → "Show me laptops with 16GB RAM that have SSD"

# Example 3: Already standalone
rewrite_query_with_context("Show me all orders", [])
# → "Show me all orders" (unchanged)
```

**Prompt Strategy**:
- Includes full conversation history
- Instructs LLM to resolve pronouns and implicit references
- Preserves original intent and specificity
- Returns only the rewritten query (no explanations)

### 3. Updated Assistant Methods

All three RAG assistants (`admin_assistant.py`, `user_assistant.py`, `visitor_assistant.py`) now have updated `process_query()` methods:

#### Admin Assistant
```python
def process_query(
    self, 
    query: str, 
    customer_id: Optional[int] = None, 
    role: Optional[str] = None,
    session_id: Optional[str] = None,  # ← NEW
    return_debug: bool = False
) -> Any
```

#### User Assistant
```python
def process_query(
    self, 
    query: str, 
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,  # ← NEW
    return_debug: bool = False
) -> Any
```

#### Visitor Assistant
```python
def process_query(
    self, 
    query: str,
    session_id: Optional[str] = None,  # ← NEW
    return_debug: bool = False
) -> Any
```

### 4. API Endpoint Updates (`chat.py`)

The `/message` endpoint now passes `session_id` to all assistants:

```python
# Visitor
bot_response, debug_info = visitor_assistant.process_query(
    user_message,
    session_id=session_id,  # ← NEW
    return_debug=True
)

# Admin
bot_response, debug_info = admin_assistant.process_query(
    user_message, 
    customer_id=customer_id, 
    role=role,
    session_id=session_id,  # ← NEW
    return_debug=True
)

# User
bot_response, debug_info = user_assistant.process_query(
    user_message, 
    user_id=customer_id,
    session_id=session_id,  # ← NEW
    return_debug=True
)
```

## Debug Information

The `debug_info` dictionary now includes conversational context details:

```json
{
  "query_type": "user_query",
  "original_query": "What about in blue?",
  "rewritten_query": "Show me the previously mentioned dress in blue color",
  "has_conversation_history": true,
  "is_intro": false,
  "data_accessed": ["product"],
  "search_results_count": 5,
  "user_role": "user"
}
```

**New Fields**:
- `original_query`: The exact query the user typed
- `rewritten_query`: The standalone query used for semantic search
- `has_conversation_history`: Boolean indicating if history was available

## Configuration

### History Window Size

Default: 5 message pairs (10 total messages)

**Rationale**:
- **Too small (1-2)**: Insufficient context for complex conversations
- **Too large (10+)**: Increased token cost, potential noise, slower processing
- **Optimal (3-5)**: Balances context richness with performance

**To modify**: Change the `limit` parameter in `get_conversation_history()` calls:

```python
# In admin_assistant.py, user_assistant.py, visitor_assistant.py
conversation_history = get_conversation_history(session_id, limit=5)  # ← Adjust here
```

### LLM Model Selection

**Query Rewriting Model**: `gemini-2.0-flash-exp`
- Fast response time (critical for UX)
- Good at understanding conversational context
- Cost-effective for rewriting tasks

**To change model**:
```python
# In utils.py, rewrite_query_with_context()
model = genai.GenerativeModel('gemini-2.0-flash-exp')  # ← Change here
```

## Error Handling

### Graceful Fallbacks

1. **No conversation history**: Uses original query directly
2. **Query rewriting fails**: Returns original query with warning log
3. **Database connection error**: Catches exception, returns empty history
4. **LLM timeout**: Retries up to `max_retries` times, then uses original query

### Logging

All key operations are logged:

```python
logger.info(f"Query rewritten: '{current_query}' → '{rewritten_query}'")
logger.warning("Query rewriting failed, using original query")
logger.error(f"Error retrieving conversation history: {e}")
```

## Performance Considerations

### Token Usage

**Per Query** (with history):
- Conversation history retrieval: ~0 tokens (DB query)
- Query rewriting: ~200-500 tokens (depending on history length)
- Main RAG generation: ~1000-3000 tokens (unchanged)

**Cost Impact**: Approximately +15-20% token usage per query

### Response Time

**Typical Flow**:
1. DB query (50-100ms): Retrieve history
2. LLM call (200-500ms): Rewrite query
3. Vector search (100-300ms): Semantic search
4. LLM call (500-1500ms): Generate response

**Total added latency**: ~250-600ms for query rewriting

### Optimization Tips

1. **Cache conversation history** in Redis for frequently accessed sessions
2. **Batch rewriting** for multiple queries in same session
3. **Skip rewriting** for first message in session (no history)
4. **Monitor and adjust** history window size based on actual conversation patterns

## Testing Examples

### Test Case 1: Product Discovery with Follow-ups

```
Session: new_visitor_123

User: "Show me gaming laptops"
Rewritten: "Show me gaming laptops" (no history)
Response: [Lists gaming laptops]

User: "Under $1500"
Rewritten: "Show me gaming laptops under $1500"
Response: [Lists budget gaming laptops]

User: "With RTX graphics"
Rewritten: "Show me gaming laptops under $1500 with RTX graphics"
Response: [Lists RTX gaming laptops in budget]

User: "What's the best one?"
Rewritten: "What is the best gaming laptop under $1500 with RTX graphics?"
Response: [Recommends top option]
```

### Test Case 2: Order Tracking

```
Session: user_abc456

User: "Show me my recent orders"
Rewritten: "Show me my recent orders" (no history)
Response: [Lists user's orders]

User: "Where is the last one?"
Rewritten: "What is the shipment status of my most recent order?"
Response: [Shows tracking info]

User: "When will it arrive?"
Rewritten: "When will my most recent order arrive?"
Response: [Provides delivery estimate]
```

### Test Case 3: Admin Analytics

```
Session: admin_xyz789

User: "Show total sales this month"
Rewritten: "Show total sales this month" (no history)
Response: [Shows sales data]

User: "Compare with last month"
Rewritten: "Compare total sales this month with last month"
Response: [Shows comparison]

User: "Which products sold the most?"
Rewritten: "Which products sold the most this month?"
Response: [Top products list]
```

## Monitoring

### Key Metrics to Track

1. **Rewriting Success Rate**: % of queries successfully rewritten
2. **Rewriting Accuracy**: Manual review of rewritten queries
3. **Conversation Length**: Average number of turns per session
4. **User Satisfaction**: Improvement in follow-up query success
5. **Performance Impact**: Added latency per query

### Logging Queries

All rewritten queries are logged and stored in `metadata` JSONB field:

```sql
SELECT 
    user_message,
    metadata->>'debug'->>'original_query' as original,
    metadata->>'debug'->>'rewritten_query' as rewritten
FROM chat_history
WHERE session_id = 'abc-123'
ORDER BY timestamp;
```

## Limitations

### Current Constraints

1. **History Window**: Limited to last 5 message pairs
   - Long conversations lose early context
   - May require manual session reset for new topics

2. **Single Session Only**: No cross-session memory
   - Each session starts fresh
   - User must re-establish context after session expires

3. **Text-Only**: No support for images, voice, or multimodal context

4. **Language**: Optimized for English queries
   - May need adjustment for other languages

5. **No Explicit Memory**: Cannot remember user preferences across sessions
   - "Remember I prefer blue" won't persist

### Known Edge Cases

1. **Topic Switches**: Abrupt topic changes may confuse rewriting
   ```
   User: "Show me laptops"
   User: "What about shoes?" 
   → May incorrectly rewrite to "What about laptop shoes?"
   ```

2. **Ambiguous Pronouns**: Multiple entities in history
   ```
   User: "Show me laptops and phones"
   User: "What's the price of that one?"
   → Unclear which "that one" refers to
   ```

3. **Negations**: Complex negations may be lost
   ```
   User: "Show products except electronics"
   User: "Actually, include them"
   → May lose the reversal context
   ```

## Future Enhancements

### Potential Improvements

1. **Semantic Caching**: Cache rewritten queries for common patterns
2. **User Preferences**: Store long-term preferences in user profile
3. **Multi-Modal**: Support images in conversation context
4. **Conversation Summarization**: Summarize long histories to reduce tokens
5. **Explicit Memory Commands**: "Remember this for next time"
6. **A/B Testing**: Compare with/without query rewriting
7. **Fine-Tuned Model**: Train custom model on e-commerce conversations

## Conclusion

The conversational RAG implementation successfully enables natural multi-turn conversations by:

✅ **Maintaining Context**: Retrieves and uses conversation history  
✅ **Query Rewriting**: Transforms follow-ups into standalone queries  
✅ **Seamless Integration**: Works across all three user roles  
✅ **Transparent Debugging**: Provides clear visibility into rewriting process  
✅ **Graceful Fallbacks**: Handles errors without breaking user experience  

The system is now production-ready for conversational e-commerce interactions.
