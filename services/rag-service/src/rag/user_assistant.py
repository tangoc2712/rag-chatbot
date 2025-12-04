import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from ..config import Settings
from ..database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserECommerceRAG:
    """RAG assistant for logged-in users - access to own orders + all visitor permissions"""
    
    def __init__(self):
        """Initialize RAG system with Database and Gemini"""
        self.settings = Settings()
        
        # Initialize Gemini
        if self.settings.GOOGLE_API_KEY:
            genai.configure(api_key=self.settings.GOOGLE_API_KEY)
            self.llm = genai.GenerativeModel('gemini-2.5-flash-lite')
            logger.info("Google Gemini LLM initialized successfully for User Assistant")
        else:
            self.llm = None
            logger.warning("GOOGLE_API_KEY not found. LLM features will be limited.")
    
    def semantic_search(self, query: str, tables: List[str] = None, user_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search across specified tables using pgvector
        For users: products, product_reviews, categories, and user's own orders
        """
        if not self.settings.GOOGLE_API_KEY:
            logger.warning("Cannot perform semantic search without GOOGLE_API_KEY")
            return []

        # Users can access products, reviews, categories, and their own orders
        allowed_tables = ['product', 'product_review', 'category', 'order', 'shipment']
        tables_to_search = tables if tables else ['product', 'product_review']
        tables_to_search = [t for t in tables_to_search if t in allowed_tables]

        try:
            # Generate embedding for query
            result = genai.embed_content(
                model="models/embedding-001",
                content=query,
                task_type="retrieval_query"
            )
            query_embedding = result['embedding']
            
            conn = get_db_connection()
            results = []
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for table in tables_to_search:
                    try:
                        if table == 'product':
                            sql = """
                                SELECT 'product' as _source_table, 
                                       product_id, name, description, price, sale_price, 
                                       stock, category_name, colors, sizes, materials, product_url,
                                       embedding <=> %s::vector as distance 
                                FROM product
                                WHERE embedding IS NOT NULL AND is_active = true
                                ORDER BY distance ASC LIMIT %s
                            """
                            cur.execute(sql, [query_embedding, limit])
                        elif table == 'product_review':
                            sql = """
                                SELECT 'product_review' as _source_table,
                                       pr.rating, pr.comment, pr.created_at, p.name as product_name,
                                       pr.embedding <=> %s::vector as distance
                                FROM product_review pr
                                LEFT JOIN product p ON pr.product_id = p.product_id
                                WHERE pr.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                            cur.execute(sql, [query_embedding, limit])
                        elif table == 'category':
                            sql = """
                                SELECT 'category' as _source_table,
                                       category_id, name, type,
                                       embedding <=> %s::vector as distance
                                FROM category
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                            cur.execute(sql, [query_embedding, limit])
                        elif table == 'order' and user_id:
                            # Only fetch user's own orders
                            sql = """
                                SELECT 'order' as _source_table,
                                       o.order_id, o.status, o.order_total, o.currency, 
                                       o.created_at, o.subtotal, o.tax, o.shipping_charges, o.discount,
                                       o.embedding <=> %s::vector as distance
                                FROM "order" o
                                WHERE o.user_id = %s AND o.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                            cur.execute(sql, [query_embedding, user_id, limit])
                        elif table == 'shipment' and user_id:
                            # Only fetch shipments for user's orders
                            sql = """
                                SELECT 'shipment' as _source_table,
                                       s.shipment_id, s.tracking_number, s.status, s.shipped_at, s.delivered_at,
                                       o.order_id,
                                       s.embedding <=> %s::vector as distance
                                FROM shipment s
                                JOIN "order" o ON s.order_id = o.order_id
                                WHERE o.user_id = %s AND s.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                            cur.execute(sql, [query_embedding, user_id, limit])
                        else:
                            continue
                        
                        table_results = cur.fetchall()
                        results.extend(table_results)
                    except Exception as e:
                        logger.warning(f"Error searching table {table}: {e}")
                        continue
            
            # Sort all results by distance and limit
            results.sort(key=lambda x: x.get('distance', 999))
            return results[:limit * 2]
                
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def generate_llm_response(self, query: str, context: str, is_intro_query: bool = False) -> str:
        """Generate natural language response using Gemini"""
        if not self.llm:
            return context
        
        intro_message = ""
        if is_intro_query:
            intro_message = """
When users ask who you are or about yourself, give a brief introduction:
"Hi! I'm your personal shopping assistant. I can help you with:
- **Your Orders** - Track status and history
- **Products** - Find items and check details
- **Reviews** - See what others think

What can I help you with?"
"""
        
        prompt = f"""
You are a helpful PERSONAL ASSISTANT for a logged-in customer. Be friendly but concise.

YOUR STYLE:
- Friendly and personal, but keep responses SHORT
- Use emojis sparingly (1-2 per response maximum)
- Get straight to the answer
- Be warm but efficient

WHAT YOU CAN ACCESS:
- Customer's own orders (status, items, history)
- Order shipments and tracking
- Products (names, descriptions, prices, stock, colors, sizes, materials, product_url)
- Product reviews and ratings
- Product categories

WHAT YOU CANNOT ACCESS:
- Other customers' data
- Admin-level information
- Payment details

{intro_message}

HOW TO RESPOND:
1. Answer the question directly first
2. Include product links when mentioning products
3. For orders: provide status, dates, and key details clearly
4. Keep suggestions brief - max 2-3 recommendations
5. End with ONE short follow-up question if appropriate
6. Avoid repetitive phrases and excessive enthusiasm

FORMATTING:
- Show prices: "$29.99" or "~~$39.99~~ **$29.99**"
- Include product links when available
- Show ratings: "4.8/5 ⭐"
- Order status: use clear labels like "Shipped", "Delivered", "Processing"
- Use bullet points for multiple items
- Keep total response under 150 words when possible

Context from database:
{context}

Customer's Question: {query}

Respond concisely and helpfully:
"""
        
        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return context if context else "I'm sorry, I couldn't process your request. Please try again."
    
    def process_query(self, query: str, user_id: Optional[str] = None,
                     session_id: Optional[str] = None, return_debug: bool = False) -> Any:
        """Process user query with access to own orders + products/reviews
        
        Args:
            query: User's question
            user_id: The authenticated user's ID (for accessing their own orders)
            session_id: Optional session ID for conversational context
            return_debug: If True, return tuple of (response, debug_info)
        
        Returns:
            str or tuple: Response text, or (response, debug_info) if return_debug=True
        """
        from .utils import get_conversation_history, rewrite_query_with_context
        
        query_lower = query.lower()
        original_query = query
        
        # Retrieve conversation history and rewrite query if needed
        rewritten_query = query
        conversation_history = []
        if session_id:
            conversation_history = get_conversation_history(session_id, limit=5)
            if conversation_history:
                rewritten_query = rewrite_query_with_context(query, conversation_history)
                query_lower = rewritten_query.lower()
        
        # Check if this is an introduction/greeting query
        is_intro_query = any(word in query_lower for word in [
            'who are you', 'what are you', 'what can you do', 
            'introduce yourself', 'your capabilities', 'hello', 'hi', 'hey'
        ])
        
        context_parts = []
        debug_info = {
            'query_type': 'user_query',
            'user_id': user_id,
            'original_query': original_query,
            'rewritten_query': rewritten_query,
            'has_conversation_history': len(conversation_history) > 0,
            'is_intro': is_intro_query,
            'data_accessed': []
        }
        
        try:
            # Handle admin-only requests
            admin_keywords = ['all orders', 'all users', 'all customers', 'revenue report', 
                             'sales report', 'admin', 'dashboard', 'analytics', 'total revenue']
            if any(word in query_lower for word in admin_keywords):
                context_parts.append(
                    "ADMIN_ONLY: The user is asking about admin-level features. "
                    "Politely explain that you can only help with their personal orders and product browsing. "
                    "Suggest contacting support for admin-level inquiries."
                )
                debug_info['data_accessed'].append('admin_only_notice')
            
            # Determine which tables to search based on query
            tables_to_search = []
            
            # Check for user's own order queries
            if user_id and any(word in query_lower for word in ['my order', 'my orders', 'order status', 
                                                                  'track order', 'my purchase', 'order history',
                                                                  'where is my', 'delivery', 'shipping']):
                tables_to_search.append('order')
                tables_to_search.append('shipment')
                debug_info['data_accessed'].append('user_orders')
                debug_info['data_accessed'].append('user_shipments')
            
            # Check for review queries
            if any(word in query_lower for word in ['review', 'rating', 'feedback', 'opinion']):
                tables_to_search.append('product_review')
                debug_info['data_accessed'].append('reviews')
            
            # Check for category queries
            if any(word in query_lower for word in ['category', 'categories', 'type', 'kinds']):
                tables_to_search.append('category')
                debug_info['data_accessed'].append('categories')
            
            # Check for product queries
            if any(word in query_lower for word in ['product', 'item', 'buy', 'price', 'stock', 
                                                     'available', 'find', 'search', 'looking for',
                                                     'featured', 'popular', 'best', 'recommend', 'suggestion']):
                tables_to_search.append('product')
                debug_info['data_accessed'].append('product')
            
            # If no specific table matched, search products by default (unless intro query)
            if not tables_to_search and not is_intro_query:
                tables_to_search = ['product', 'product_review']
                if user_id:
                    tables_to_search.append('order')
                debug_info['data_accessed'].append('general_search')
            
            # Perform semantic search using the rewritten query
            if tables_to_search:
                search_results = self.semantic_search(rewritten_query, tables_to_search, user_id=user_id, limit=8)
                if search_results:
                    context_parts.append(f"Relevant Results: {search_results}")
                    debug_info['search_results_count'] = len(search_results)
                else:
                    # Fallback: fetch some products directly if semantic search returns nothing
                    conn = get_db_connection()
                    try:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            cur.execute("""
                                SELECT product_id, name, description, price, sale_price, 
                                       stock, category_name, colors, sizes, materials, product_url
                                FROM product 
                                WHERE is_active = true 
                                ORDER BY RANDOM() 
                                LIMIT 5
                            """)
                            fallback_products = cur.fetchall()
                            if fallback_products:
                                context_parts.append(f"Available Products: {fallback_products}")
                                debug_info['fallback_products'] = len(fallback_products)
                    except Exception as e:
                        logger.warning(f"Fallback query failed: {e}")
                    finally:
                        conn.close()
            
            # Add general stats if needed
            if not context_parts and not is_intro_query:
                conn = get_db_connection()
                try:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("SELECT COUNT(*) as total_products FROM product WHERE is_active = true")
                        stats = cur.fetchone()
                        context_parts.append(f"We have {stats['total_products']} products available.")
                        
                        if user_id:
                            cur.execute("SELECT COUNT(*) as order_count FROM \"order\" WHERE user_id = %s", (user_id,))
                            order_stats = cur.fetchone()
                            context_parts.append(f"You have {order_stats['order_count']} orders in your history.")
                finally:
                    conn.close()
                debug_info['data_accessed'].append('general_stats')
        
        except Exception as e:
            logger.error(f"Error fetching database context: {e}")
            context_parts.append("I encountered an issue retrieving information. Please try again.")
            debug_info['error'] = str(e)
        
        # Combine all context
        context = "\n\n".join(context_parts) if context_parts else "No specific data retrieved."
        
        # Generate response with LLM using the original query for natural conversation
        response = self.generate_llm_response(original_query, context, is_intro_query=is_intro_query)
        
        if return_debug:
            return response, debug_info
        return response
