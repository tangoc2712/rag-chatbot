import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import numpy as np
import google.generativeai as genai
import os
import logging

logger = logging.getLogger(__name__)

def preprocess_text(text: str) -> str:
    """
    Preprocess text for better matching
    
    Args:
        text: Input text to preprocess
    
    Returns:
        Preprocessed text
    """
    if not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    return text

def calculate_semantic_similarity(
    query_embedding: np.ndarray,
    document_embeddings: np.ndarray
) -> np.ndarray:
    """
    Calculate cosine similarity between query and documents
    
    Args:
        query_embedding: Query embedding vector
        document_embeddings: Matrix of document embeddings
    
    Returns:
        Array of similarity scores
    """
    # Normalize vectors
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    doc_norms = document_embeddings / np.linalg.norm(document_embeddings, axis=1, keepdims=True)
    
    # Compute cosine similarity
    return np.dot(doc_norms, query_norm)

def format_price(price: float) -> str:
    """
    Format price with proper currency symbol and decimals
    
    Args:
        price: Price value to format
    
    Returns:
        Formatted price string
    """
    return f"${price:,.2f}"

def parse_date_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse date range strings into datetime objects
    
    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
    
    Returns:
        Tuple of parsed start and end dates
    """
    parsed_start = None
    parsed_end = None
    
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid end_date format. Use YYYY-MM-DD")
    
    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise ValueError("start_date cannot be later than end_date")
    
    return parsed_start, parsed_end

def filter_dataframe_by_date(
    df: pd.DataFrame,
    date_column: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Filter DataFrame by date range
    
    Args:
        df: Input DataFrame
        date_column: Name of date column
        start_date: Start date for filtering
        end_date: End date for filtering
    
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    if start_date:
        filtered_df = filtered_df[
            pd.to_datetime(filtered_df[date_column]) >= start_date
        ]
    
    if end_date:
        filtered_df = filtered_df[
            pd.to_datetime(filtered_df[date_column]) <= end_date
        ]
    
    return filtered_df

def calculate_order_statistics(orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate summary statistics for orders
    
    Args:
        orders_df: DataFrame containing order data
    
    Returns:
        Dictionary of summary statistics
    """
    stats = {
        "total_orders": len(orders_df),
        "total_sales": float(orders_df['Sales'].sum()),
        "average_order_value": float(orders_df['Sales'].mean()),
        "total_shipping_cost": float(orders_df['Shipping_Cost'].sum()),
        "orders_by_priority": orders_df['Order_Priority'].value_counts().to_dict(),
        "orders_by_category": orders_df['Product_Category'].value_counts().to_dict()
    }
    
    return stats

def format_product_response(product: Dict[str, Any], include_score: bool = False) -> str:
    """
    Format product information into a readable string
    
    Args:
        product: Dictionary containing product information
        include_score: Whether to include similarity score
    
    Returns:
        Formatted product string
    """
    response = []
    response.append(f"- {product['Product_Title']}")
    response.append(f"  Price: {format_price(product['Price'])}")
    response.append(f"  Rating: {product['Rating']:.1f} stars")
    
    if 'Description' in product and product['Description']:
        description = product['Description'][:100]
        response.append(f"  Description: {description}...")
    
    if include_score and 'similarity_score' in product:
        response.append(f"  Relevance: {product['similarity_score']:.2f}")
    
    return "\n".join(response)

def format_order_response(order: Dict[str, Any]) -> str:
    """
    Format order information into a readable string
    
    Args:
        order: Dictionary containing order information
    
    Returns:
        Formatted order string
    """
    response = []
    response.append("Order Details:")
    response.append(f"- Date: {order.get('Order_Date', 'Unknown Date')}")
    response.append(f"- Product: {order.get('Product_Category', 'Unknown Product')}")
    response.append(f"- Total: {format_price(order.get('Sales', 0))}")
    response.append(f"- Shipping: {format_price(order.get('Shipping_Cost', 0))}")
    response.append(f"- Priority: {order.get('Order_Priority', 'N/A')}")
    
    return "\n".join(response)


def get_conversation_history(session_id: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Retrieve recent conversation history from chat_history table.
    
    Args:
        session_id: The session ID to fetch history for
        limit: Maximum number of message pairs to retrieve (default: 5)
    
    Returns:
        List of conversation history dicts with 'user_message' and 'bot_response'
        Ordered from oldest to newest
    """
    from ..database import get_db_connection
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get the most recent messages (DESC) then reverse to get chronological order
        cur.execute("""
            SELECT user_message, bot_response, timestamp
            FROM chat_history
            WHERE session_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (session_id, limit))
        
        rows = cur.fetchall()
        
        # Reverse to get chronological order (oldest to newest)
        history = []
        for row in reversed(rows):
            history.append({
                'user_message': row[0],
                'bot_response': row[1],
                'timestamp': row[2].isoformat() if row[2] else None
            })
        
        cur.close()
        conn.close()
        
        return history
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        return []


def rewrite_query_with_context(
    current_query: str, 
    conversation_history: List[Dict[str, str]],
    max_retries: int = 2
) -> str:
    """
    Use LLM to rewrite a follow-up query into a standalone, context-independent question.
    This is crucial for RAG systems to handle conversational follow-ups correctly.
    
    Args:
        current_query: The current user query that may contain references to previous context
        conversation_history: List of previous message pairs (user_message, bot_response)
        max_retries: Maximum number of retry attempts if LLM fails
    
    Returns:
        Rewritten standalone query suitable for vector search
    """
    # If no history, return original query
    if not conversation_history:
        return current_query
    
    # Build conversation context
    context_lines = []
    for msg in conversation_history:
        context_lines.append(f"User: {msg['user_message']}")
        context_lines.append(f"Assistant: {msg['bot_response']}")
    
    conversation_context = "\n".join(context_lines)
    
    # Create prompt for query rewriting
    prompt = f"""You are a query rewriting assistant for an e-commerce RAG system. Your task is to rewrite follow-up questions into standalone, self-contained queries that can be used for semantic search.

Conversation History:
{conversation_context}

Current Follow-up Question: {current_query}

Instructions:
1. **CRITICAL FOR ORDER QUERIES**: Look for order IDs in the Assistant's responses (format: #abc123 or "Order #abc123" or order_id values like "a1b2c3d4-...")
2. If the current question refers to "this order", "that order", "the order", or "these items", extract the EXACT order_id from the conversation history
3. Replace pronouns (it, that, they, these) with explicit entities from the conversation
4. If the question is already standalone and clear, return it as-is
5. Preserve the original intent and specificity of the question
6. Keep it concise - don't add unnecessary context, just make it standalone

Examples:
- "What about in blue?" → "Show me [previous product] in blue color"
- "How much does it cost?" → "What is the price of [previous product]?"
- "Show me my recent orders" → "Show me my recent orders" (already standalone)
- "What items are in this order?" (after bot showed "Order #a1b2c3d4") → "What items are in order a1b2c3d4?"
- "What's in the order?" (after bot mentioned order_id: xyz-456) → "Show me items in order xyz-456"
- "what are these items of this order?" (after bot showed order #abc123) → "What are the items in order abc123?"

Rewritten Query (respond with ONLY the rewritten query, no explanations):"""

    try:
        # Configure Gemini API
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found, returning original query")
            return current_query
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Attempt query rewriting with retries
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                rewritten_query = response.text.strip()
                
                # Validate the rewritten query
                if rewritten_query and len(rewritten_query) > 3:
                    logger.info(f"Query rewritten: '{current_query}' → '{rewritten_query}'")
                    return rewritten_query
                else:
                    logger.warning(f"Invalid rewritten query (attempt {attempt + 1}): '{rewritten_query}'")
                    
            except Exception as e:
                logger.error(f"Error in query rewriting attempt {attempt + 1}: {e}")
                
        # If all retries fail, return original query
        logger.warning("Query rewriting failed, using original query")
        return current_query
        
    except Exception as e:
        logger.error(f"Fatal error in query rewriting: {e}")
        return current_query
