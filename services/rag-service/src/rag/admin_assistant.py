import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from ..config import Settings
from ..database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECommerceRAG:
    """RAG assistant for admin users - full access to all data"""
    
    def __init__(self):
        """Initialize RAG system with Database and Gemini"""
        self.settings = Settings()
        
        # Initialize Gemini
        if self.settings.GOOGLE_API_KEY:
            genai.configure(api_key=self.settings.GOOGLE_API_KEY)
            self.llm = genai.GenerativeModel('gemini-2.5-flash-lite')
            logger.info("Google Gemini LLM initialized successfully")
        else:
            self.llm = None
            logger.warning("GOOGLE_API_KEY not found. LLM features will be limited.")

    def semantic_search(self, query: str, tables: List[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search across multiple tables using pgvector
        Admin has access to all tables
        """
        if not self.settings.GOOGLE_API_KEY:
            logger.warning("Cannot perform semantic search without GOOGLE_API_KEY")
            return []

        # All tables available to admin
        all_tables = ['product', 'user', 'order', 'order_item', 'product_review', 'category', 
                      'cart', 'cart_item', 'payment', 'shipment', 'inventory', 'coupon', 'event']
        
        # Determine which tables to search
        if tables:
            tables_to_search = [t for t in tables if t in all_tables]
        else:
            # Auto-detect relevant tables based on query keywords
            query_lower = query.lower()
            tables_to_search = []
            
            if any(word in query_lower for word in ['product', 'item', 'buy', 'purchase', 'price', 'rating']):
                tables_to_search.append('product')
            if any(word in query_lower for word in ['user', 'customer', 'profile', 'account']):
                tables_to_search.append('user')
            if any(word in query_lower for word in ['order', 'purchase history', 'bought']):
                tables_to_search.append('order')
            if any(word in query_lower for word in ['order item', 'items in order', 'order contents', 'products in order']):
                tables_to_search.append('order_item')
            if any(word in query_lower for word in ['review', 'comment', 'feedback', 'rating']):
                tables_to_search.append('product_review')
            if any(word in query_lower for word in ['cart', 'shopping cart']):
                tables_to_search.extend(['cart', 'cart_item'])
            if any(word in query_lower for word in ['payment', 'transaction', 'paid']):
                tables_to_search.append('payment')
            if any(word in query_lower for word in ['shipment', 'shipping', 'delivery', 'ship']):
                tables_to_search.append('shipment')
            if any(word in query_lower for word in ['inventory', 'stock', 'available']):
                tables_to_search.append('inventory')
            if any(word in query_lower for word in ['coupon', 'discount', 'promo']):
                tables_to_search.append('coupon')
            if any(word in query_lower for word in ['event', 'activity']):
                tables_to_search.append('event')
            if any(word in query_lower for word in ['category', 'categories']):
                tables_to_search.append('category')
            
            # Default to products if no match
            if not tables_to_search:
                tables_to_search = ['product']

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
                        # Build table-specific query
                        if table == 'product':
                            sql = """
                                SELECT 'product' as _source_table, 
                                       product_id, name, description, price, sale_price, 
                                       stock, category_name, colors, sizes, materials, product_url,
                                       photos, care, featured,
                                       embedding <=> %s::vector as distance 
                                FROM product
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'user':
                            sql = """
                                SELECT 'user' as _source_table,
                                       user_id, full_name, email, phone, address, job, gender, role, city, country,
                                       embedding <=> %s::vector as distance
                                FROM "user"
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'order':
                            sql = """
                                SELECT 'order' as _source_table,
                                       order_id, user_id, status, order_total, currency, 
                                       subtotal, tax, shipping_charges, discount, created_at,
                                       embedding <=> %s::vector as distance
                                FROM "order"
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'order_item':
                            sql = """
                                SELECT 'order_item' as _source_table,
                                       oi.order_item_id, oi.order_id, oi.product_id, 
                                       oi.quantity, oi.unit_price, oi.total_price,
                                       p.name as product_name, p.description as product_description,
                                       o.status as order_status, o.created_at as order_date,
                                       o.user_id,
                                       oi.embedding <=> %s::vector as distance
                                FROM order_item oi
                                JOIN "order" o ON oi.order_id = o.order_id
                                LEFT JOIN product p ON oi.product_id = p.product_id
                                WHERE oi.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'product_review':
                            sql = """
                                SELECT 'product_review' as _source_table,
                                       pr.product_review_id, pr.rating, pr.comment, pr.created_at, 
                                       p.name as product_name,
                                       pr.embedding <=> %s::vector as distance
                                FROM product_review pr
                                LEFT JOIN product p ON pr.product_id = p.product_id
                                WHERE pr.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'payment':
                            sql = """
                                SELECT 'payment' as _source_table,
                                       payment_id, order_id, amount, method, status, paid_at,
                                       embedding <=> %s::vector as distance
                                FROM payment
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'shipment':
                            sql = """
                                SELECT 'shipment' as _source_table,
                                       shipment_id, order_id, tracking_number, status, 
                                       shipped_at, delivered_at,
                                       embedding <=> %s::vector as distance
                                FROM shipment
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'coupon':
                            sql = """
                                SELECT 'coupon' as _source_table,
                                       coupon_id, code, discount_type, value, valid_from, valid_to, usage_count,
                                       embedding <=> %s::vector as distance
                                FROM coupon
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'inventory':
                            sql = """
                                SELECT 'inventory' as _source_table,
                                       i.inventory_id, i.product_id, i.quantity, i.last_updated,
                                       p.name as product_name,
                                       i.embedding <=> %s::vector as distance
                                FROM inventory i
                                LEFT JOIN product p ON i.product_id = p.product_id
                                WHERE i.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'category':
                            sql = """
                                SELECT 'category' as _source_table,
                                       category_id, name, type,
                                       embedding <=> %s::vector as distance
                                FROM category
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'cart':
                            sql = """
                                SELECT 'cart' as _source_table,
                                       cart_id, user_id, status, total_price, created_at,
                                       embedding <=> %s::vector as distance
                                FROM cart
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'cart_item':
                            sql = """
                                SELECT 'cart_item' as _source_table,
                                       ci.cart_item_id, ci.cart_id, ci.quantity, ci.unit_price, ci.total_price,
                                       p.name as product_name,
                                       ci.embedding <=> %s::vector as distance
                                FROM cart_item ci
                                LEFT JOIN product p ON ci.product_id = p.product_id
                                WHERE ci.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'event':
                            sql = """
                                SELECT 'event' as _source_table,
                                       event_id, user_id, event_type, session_id, ts,
                                       embedding <=> %s::vector as distance
                                FROM event
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        else:
                            continue
                        
                        cur.execute(sql, [query_embedding, limit])
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
        
        # Special handling for introduction/greeting queries
        intro_message = ""
        if is_intro_query:
            intro_message = """
When users ask who you are, give a brief introduction:
"I'm the Admin Analytics Assistant. I provide accurate data on orders, users, products, payments, shipments, inventory, and all business metrics. What data do you need?"
"""
        
        prompt = f"""
You are a DATA ANALYST ASSISTANT for e-commerce administrators. Provide accurate, complete, and direct answers.

YOUR ROLE:
- Provide precise data and statistics
- Answer questions directly without unnecessary advice or suggestions
- Focus on numbers, facts, and completeness
- Be professional and concise

DATA YOU CAN ACCESS:
- Orders: counts, totals, status, history, items
- Order Items: products in specific orders, quantities, prices per order
- Users/Customers: counts, profiles, activity
- Products: inventory, prices, categories, stock levels, photos, product_url
- Payments: amounts, status, methods, totals
- Shipments: status, tracking, delivery info
- Reviews: ratings, counts, averages
- Coupons: codes, discounts, usage
- Carts: items, totals, abandoned carts
- Inventory: stock levels, availability

IMPORTANT - TRACKING ORDER IDs:
- When you mention an order in your response, ALWAYS remember its order_id
- If the user asks a follow-up question about "this order", "that order", or "the order", use the order_id from the most recent order you discussed
- The context may contain order_id fields - extract and use them for follow-up queries about order items

{intro_message}

HOW TO RESPOND:
1. **Answer directly** - Start with the exact data requested
2. **Be complete** - Include all relevant numbers and details
3. **Be accurate** - Double-check calculations and totals
4. **Product recommendations** - Format each product as a JSON object on its own line:
   {{"type":"product","name":"Product Name","price":29.99,"sale_price":19.99,"image":"https://...","url":"https://...","stock":50,"colors":[],"sizes":["S","M","L"]}}
5. **Order information** - Format each order as a JSON object on its own line:
   {{"type":"order","order_id":"abc-123","status":"Delivered","total":161.64,"currency":"USD","placed_date":"2025-10-15","url":"https://hackathon-478514.web.app/order/abc-123","items_count":2,"item_names":["Product 1","Product 2"]}}
6. **No advice** - Don't give business suggestions unless asked
7. **No small talk** - Skip greetings and pleasantries
8. **Structured format** - Use tables or lists for multiple items

FORMATTING RULES FOR PRODUCTS:
- Each product MUST be on a separate line as valid JSON
- Use the FIRST photo from the photos array as "image"
- Show original price and sale_price (use null if no sale)
- Include product_url as "url"
- Include available colors and sizes arrays

FORMATTING RULES FOR ORDERS:
- Each order MUST be on a separate line as valid JSON with type="order"
- Include order_id, status, total, currency, placed_date
- URL format: "https://hackathon-478514.web.app/order/{{order_id}}"
- Include items_count and item_names array (list of product names in the order)
- Status should be clear: "Delivered", "Shipped", "Processing", "Cancelled", etc.

FORMATTING RULES FOR ORDER ITEMS:
- When showing items in an order, list each item with product name, quantity, unit price, and total
- Format: "- [Product Name] x[quantity] @ $[unit_price] = $[total_price]"
- Include order_id reference when listing items

GENERAL FORMATTING:
- Use **bold** for key numbers and important values
- Use tables for comparing data when appropriate
- Use bullet points for lists
- Show currency with proper formatting: **$1,234.56**
- Show percentages clearly: **45.2%**
- For counts: **Total: 150 orders**
- Keep responses focused and scannable

EXAMPLE RESPONSES:

Q: "How many orders this month?"
A: "**Total Orders (This Month): 245**
- Completed: 180
- Processing: 45
- Pending: 20
**Total Revenue: $34,567.89**"

Q: "Top selling products?"
A: "**Top 5 Products by Sales:**
1. Product A - 156 units ($4,680)
2. Product B - 134 units ($2,680)
3. Product C - 98 units ($1,960)
4. Product D - 87 units ($2,610)
5. Product E - 76 units ($1,520)"

IMPORTANT:
- Never use emojis
- Don't add motivational comments or suggestions
- Don't say "Great question!" or similar phrases
- Present data cleanly without commentary
- If data is incomplete or unavailable, state it clearly

Admin Question: {query}

Retrieved Data:
{context}

Provide a direct, accurate, and complete answer:
"""
        
        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return f"I found some information but couldn't generate a summary. Here is the raw data:\n\n{context}"

    def process_query(self, query: str, customer_id: Optional[int] = None, 
                     role: Optional[str] = None, session_id: Optional[str] = None,
                     return_debug: bool = False) -> Any:
        """Process admin query with access to all data
        
        Args:
            query: User's question
            customer_id: Optional customer ID (admin can access any data)
            role: User's role (should be 'admin')
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
        
        # Check if this is an introduction/greeting query (but not order-related queries)
        is_intro_query = any(word in query_lower for word in [
            'who are you', 'what are you', 'what can you do', 
            'introduce yourself', 'your capabilities'
        ]) and not any(word in query_lower for word in ['order', 'item', 'product', 'purchase'])
        
        # Separate check for greetings that don't conflict with queries
        is_greeting = query_lower.strip() in ['hello', 'hi', 'hey'] or query_lower.startswith(('hello ', 'hi ', 'hey '))
        if is_greeting:
            is_intro_query = True
        
        context_parts = []
        debug_info = {
            'query_type': 'admin_query',
            'original_query': original_query,
            'rewritten_query': rewritten_query,
            'has_conversation_history': len(conversation_history) > 0,
            'is_intro': is_intro_query,
            'data_accessed': []
        }
        
        try:
            # Determine which tables to search based on query
            tables_to_search = []
            
            # Check for customer/user queries
            if any(word in query_lower for word in ['customer', 'user', 'profile', 'account']):
                tables_to_search.append('user')
                debug_info['data_accessed'].append('users')
            
            # Check for product queries
            if any(word in query_lower for word in ['product', 'item', 'inventory', 'stock']):
                tables_to_search.append('product')
                tables_to_search.append('inventory')
                debug_info['data_accessed'].append('products')
            
            # Check for order queries
            if any(word in query_lower for word in ['order', 'purchase', 'transaction']):
                tables_to_search.append('order')
                debug_info['data_accessed'].append('orders')
            
            # Check for order item queries
            if any(word in query_lower for word in ['items in', 'products in', 'order item', 
                                                      'items in order', 'items in this order',
                                                      'what\'s in', 'order contents', 'order details']):
                tables_to_search.append('order_item')
                tables_to_search.append('order')
                debug_info['data_accessed'].append('order_items')
                debug_info['data_accessed'].append('orders')
            
            # Check for payment queries
            if any(word in query_lower for word in ['payment', 'revenue', 'sales', 'paid']):
                tables_to_search.append('payment')
                debug_info['data_accessed'].append('payments')
            
            # Check for shipment queries
            if any(word in query_lower for word in ['shipment', 'shipping', 'delivery']):
                tables_to_search.append('shipment')
                debug_info['data_accessed'].append('shipments')
            
            # Check for review queries
            if any(word in query_lower for word in ['review', 'rating', 'feedback']):
                tables_to_search.append('product_review')
                debug_info['data_accessed'].append('reviews')
            
            # Check for category queries
            if any(word in query_lower for word in ['category', 'categories']):
                tables_to_search.append('category')
                debug_info['data_accessed'].append('categories')
            
            # Check for coupon queries
            if any(word in query_lower for word in ['coupon', 'discount', 'promo']):
                tables_to_search.append('coupon')
                debug_info['data_accessed'].append('coupons')
            
            # Check for cart queries
            if any(word in query_lower for word in ['cart', 'shopping cart']):
                tables_to_search.append('cart')
                tables_to_search.append('cart_item')
                debug_info['data_accessed'].append('carts')
            
            # Check for event/activity queries
            if any(word in query_lower for word in ['event', 'activity', 'action']):
                tables_to_search.append('event')
                debug_info['data_accessed'].append('events')
            
            # If no specific table matched, search main tables (unless intro query)
            if not tables_to_search and not is_intro_query:
                tables_to_search = ['product', 'order', 'user']
                debug_info['data_accessed'].append('general_search')
            
            # Perform semantic search using the rewritten query
            if tables_to_search:
                search_results = self.semantic_search(rewritten_query, tables_to_search, limit=8)
                if search_results:
                    context_parts.append(f"Relevant Results: {search_results}")
                    debug_info['search_results_count'] = len(search_results)
            
            # Add general stats if needed
            if not context_parts and not is_intro_query:
                conn = get_db_connection()
                try:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            SELECT 
                                (SELECT COUNT(*) FROM "user") as total_users,
                                (SELECT COUNT(*) FROM product) as total_products,
                                (SELECT COUNT(*) FROM "order") as total_orders
                        """)
                        stats = cur.fetchone()
                        context_parts.append(f"Database Statistics: {stats}")
                finally:
                    conn.close()
                debug_info['data_accessed'].append('general_stats')
        
        except Exception as e:
            logger.error(f"Error fetching database context: {e}")
            context_parts.append(f"Database query error: {e}")
            debug_info['error'] = str(e)
        
        # Combine all context
        context = "\n\n".join(context_parts) if context_parts else "No specific data retrieved."
        
        # Generate response with LLM using the rewritten query for context-aware responses
        response = self.generate_llm_response(rewritten_query, context, is_intro_query=is_intro_query)
        
        if return_debug:
            return response, debug_info
        return response
