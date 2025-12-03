import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from ..config import Settings

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

    def get_db_connection(self):
        return psycopg2.connect(
            host=self.settings.DB_HOST,
            port=self.settings.DB_PORT,
            user=self.settings.DB_USER,
            password=self.settings.DB_PASSWORD,
            dbname=self.settings.DB_NAME
        )

    def semantic_search(self, query: str, tables: List[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search across multiple tables using pgvector
        Admin has access to all tables
        """
        if not self.settings.GOOGLE_API_KEY:
            logger.warning("Cannot perform semantic search without GOOGLE_API_KEY")
            return []

        # All tables available to admin
        all_tables = ['products', 'users', 'orders', 'product_review', 'category', 
                      'carts', 'cart_items', 'payments', 'shipments', 'inventory', 'coupons', 'events']
        
        # Determine which tables to search
        if tables:
            tables_to_search = [t for t in tables if t in all_tables]
        else:
            # Auto-detect relevant tables based on query keywords
            query_lower = query.lower()
            tables_to_search = []
            
            if any(word in query_lower for word in ['product', 'item', 'buy', 'purchase', 'price', 'rating']):
                tables_to_search.append('products')
            if any(word in query_lower for word in ['user', 'customer', 'profile', 'account']):
                tables_to_search.append('users')
            if any(word in query_lower for word in ['order', 'purchase history', 'bought']):
                tables_to_search.append('orders')
            if any(word in query_lower for word in ['review', 'comment', 'feedback', 'rating']):
                tables_to_search.append('product_review')
            if any(word in query_lower for word in ['cart', 'shopping cart']):
                tables_to_search.extend(['carts', 'cart_items'])
            if any(word in query_lower for word in ['payment', 'transaction', 'paid']):
                tables_to_search.append('payments')
            if any(word in query_lower for word in ['shipment', 'shipping', 'delivery', 'ship']):
                tables_to_search.append('shipments')
            if any(word in query_lower for word in ['inventory', 'stock', 'available']):
                tables_to_search.append('inventory')
            if any(word in query_lower for word in ['coupon', 'discount', 'promo']):
                tables_to_search.append('coupons')
            if any(word in query_lower for word in ['event', 'activity']):
                tables_to_search.append('events')
            if any(word in query_lower for word in ['category', 'categories']):
                tables_to_search.append('category')
            
            # Default to products if no match
            if not tables_to_search:
                tables_to_search = ['products']

        try:
            # Generate embedding for query
            result = genai.embed_content(
                model="models/embedding-001",
                content=query,
                task_type="retrieval_query"
            )
            query_embedding = result['embedding']
            
            conn = self.get_db_connection()
            results = []
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for table in tables_to_search:
                    try:
                        # Build table-specific query
                        if table == 'products':
                            sql = """
                                SELECT 'products' as _source_table, 
                                       product_id, name, description, price, sale_price, 
                                       stock, category_name, colors, sizes, materials, product_url,
                                       embedding <=> %s::vector as distance 
                                FROM products
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'users':
                            sql = """
                                SELECT 'users' as _source_table,
                                       user_id, full_name, email, phone, address, job, gender, role,
                                       embedding <=> %s::vector as distance
                                FROM "user"
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'orders':
                            sql = """
                                SELECT 'orders' as _source_table,
                                       order_id, user_id, status, order_total, currency, 
                                       subtotal, tax, shipping_charges, discount, created_at,
                                       embedding <=> %s::vector as distance
                                FROM orders
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'product_review':
                            sql = """
                                SELECT 'product_review' as _source_table,
                                       pr.rating, pr.review_text, pr.created_at, p.name as product_name,
                                       pr.embedding <=> %s::vector as distance
                                FROM product_review pr
                                LEFT JOIN products p ON pr.product_id::text = p.product_id::text
                                WHERE pr.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'payments':
                            sql = """
                                SELECT 'payments' as _source_table,
                                       payment_id, order_id, amount, method, status, paid_at,
                                       embedding <=> %s::vector as distance
                                FROM payments
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'shipments':
                            sql = """
                                SELECT 'shipments' as _source_table,
                                       shipment_id, order_id, tracking_number, carrier, status, 
                                       shipped_at, delivered_at,
                                       embedding <=> %s::vector as distance
                                FROM shipments
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'coupons':
                            sql = """
                                SELECT 'coupons' as _source_table,
                                       coupon_id, code, discount_type, value, valid_from, valid_to, usage_count,
                                       embedding <=> %s::vector as distance
                                FROM coupons
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
                                LEFT JOIN products p ON i.product_id = p.product_id
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
                        elif table == 'carts':
                            sql = """
                                SELECT 'carts' as _source_table,
                                       cart_id, user_id, status, total_price, created_at,
                                       embedding <=> %s::vector as distance
                                FROM carts
                                WHERE embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'cart_items':
                            sql = """
                                SELECT 'cart_items' as _source_table,
                                       ci.cart_item_id, ci.cart_id, ci.quantity, ci.unit_price, ci.total_price,
                                       p.name as product_name,
                                       ci.embedding <=> %s::vector as distance
                                FROM cart_items ci
                                LEFT JOIN products p ON ci.product_id = p.product_id
                                WHERE ci.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                        elif table == 'events':
                            sql = """
                                SELECT 'events' as _source_table,
                                       event_id, user_id, event_type, session_id, ts,
                                       embedding <=> %s::vector as distance
                                FROM events
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
When users ask who you are or about yourself, introduce yourself in a friendly, approachable way:
"Hi! I'm your AI shopping assistant! 👋 I'm here to help you find products, track your orders, check reviews, and answer any questions about our store. Feel free to ask me anything!"
"""
        
        prompt = f"""
You are a friendly and helpful AI shopping assistant for an e-commerce platform. You help customers in a warm, conversational way.

YOUR PERSONALITY:
- Speak like a friendly store assistant, not a technical database admin
- Use simple, everyday language that anyone can understand
- Be enthusiastic and helpful, like you're chatting with a friend
- Show empathy and understanding of customer needs
- Make shopping easy and enjoyable

WHAT YOU CAN HELP WITH:
- Products: Find items, check prices, stock availability, categories, colors, sizes, materials
- Orders: Track order status, view order history, check order totals and details
- Shopping: Check cart items, find active carts, review cart totals
- Payments: View payment status, methods, transaction amounts
- Shipping: Track shipments, check delivery status, view tracking numbers
- Reviews: Read product reviews, see ratings and customer feedback
- Discounts: Find active coupons, check discount codes and amounts
- Account: View user profiles, contact info, order history
- Inventory: Check product stock levels and availability

{intro_message}

HOW TO RESPOND:
- Start with a friendly acknowledgment of their question
- Present information clearly and conversationally
- Use natural language, not technical jargon or database terms
- When showing lists, use friendly descriptions
- Add helpful context or suggestions when relevant
- Connect related information (e.g., "This order includes 3 items..." or "The customer also reviewed...")
- End with an offer to help further if appropriate

FORMATTING GUIDELINES:
- Use **bold** for important info like product names, prices, order IDs, or status
- Use emojis sparingly to add warmth:
  💰 for money/prices
  ⭐ for ratings
  📦 for orders/shipments
  🛒 for cart/shopping
  ✅ for completed/delivered status
  ⏳ for pending/processing
  🎁 for discounts/coupons
- Number items clearly: "Here are your top 5 orders:", then "1. **Order #abc123** - $300.00 💰"
- Keep it readable and scannable
- Break long responses into easy-to-read paragraphs
- Use line breaks between different items for clarity

CONNECTING THE DOTS:
- When showing orders, mention related products if available
- When showing products, mention if they're in stock or popular
- When showing users, you can mention their order count or recent activity
- Link payments to their orders
- Connect shipments to orders and delivery addresses
- Show reviews with product context

IMPORTANT: 
- Never mention "database", "SQL", "tables", "user_id", "product_id", or technical terms
- Don't show raw UUIDs unless specifically asked for order/product references
- Use friendly names: "Order #abc123" instead of showing full UUID
- Speak like you're helping a customer in person at a store
- Focus on what the customer wants to know, not how you got the data
- Make the information feel personal and relevant

User Question: {query}

Retrieved Data:
{context}

Respond in a friendly, conversational way that helps the customer understand their shopping information:
"""
        
        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return f"I found some information but couldn't generate a summary. Here is the raw data:\n\n{context}"

    def process_query(self, query: str, customer_id: Optional[int] = None, 
                     role: Optional[str] = None, return_debug: bool = False) -> Any:
        """Process admin query with access to all data
        
        Args:
            query: User's question
            customer_id: Optional customer ID (admin can access any data)
            role: User's role (should be 'admin')
            return_debug: If True, return tuple of (response, debug_info)
        
        Returns:
            str or tuple: Response text, or (response, debug_info) if return_debug=True
        """
        
        query_lower = query.lower()
        
        # Check if this is an introduction/greeting query
        is_intro_query = any(word in query_lower for word in [
            'who are you', 'what are you', 'what can you do', 
            'introduce yourself', 'your capabilities', 'hello', 'hi', 'hey'
        ])
        
        context_parts = []
        debug_info = {
            'query_type': 'admin_query',
            'is_intro': is_intro_query,
            'data_accessed': []
        }
        
        try:
            # Determine which tables to search based on query
            tables_to_search = []
            
            # Check for customer/user queries
            if any(word in query_lower for word in ['customer', 'user', 'profile', 'account']):
                tables_to_search.append('users')
                debug_info['data_accessed'].append('users')
            
            # Check for product queries
            if any(word in query_lower for word in ['product', 'item', 'inventory', 'stock']):
                tables_to_search.append('products')
                tables_to_search.append('inventory')
                debug_info['data_accessed'].append('products')
            
            # Check for order queries
            if any(word in query_lower for word in ['order', 'purchase', 'transaction']):
                tables_to_search.append('orders')
                debug_info['data_accessed'].append('orders')
            
            # Check for payment queries
            if any(word in query_lower for word in ['payment', 'revenue', 'sales', 'paid']):
                tables_to_search.append('payments')
                debug_info['data_accessed'].append('payments')
            
            # Check for shipment queries
            if any(word in query_lower for word in ['shipment', 'shipping', 'delivery']):
                tables_to_search.append('shipments')
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
                tables_to_search.append('coupons')
                debug_info['data_accessed'].append('coupons')
            
            # Check for cart queries
            if any(word in query_lower for word in ['cart', 'shopping cart']):
                tables_to_search.append('carts')
                tables_to_search.append('cart_items')
                debug_info['data_accessed'].append('carts')
            
            # Check for event/activity queries
            if any(word in query_lower for word in ['event', 'activity', 'action']):
                tables_to_search.append('events')
                debug_info['data_accessed'].append('events')
            
            # If no specific table matched, search main tables (unless intro query)
            if not tables_to_search and not is_intro_query:
                tables_to_search = ['products', 'orders', 'users']
                debug_info['data_accessed'].append('general_search')
            
            # Perform semantic search
            if tables_to_search:
                search_results = self.semantic_search(query, tables_to_search, limit=8)
                if search_results:
                    context_parts.append(f"Relevant Results: {search_results}")
                    debug_info['search_results_count'] = len(search_results)
            
            # Add general stats if needed
            if not context_parts and not is_intro_query:
                conn = self.get_db_connection()
                try:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            SELECT 
                                (SELECT COUNT(*) FROM "user") as total_users,
                                (SELECT COUNT(*) FROM products) as total_products,
                                (SELECT COUNT(*) FROM orders) as total_orders
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
        
        # Generate response with LLM
        response = self.generate_llm_response(query, context, is_intro_query=is_intro_query)
        
        if return_debug:
            return response, debug_info
        return response
