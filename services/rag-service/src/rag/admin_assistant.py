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
            self.llm = genai.GenerativeModel('gemini-2.5-flash')
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
When users ask who you are or about yourself, introduce yourself as:
"I'm an AI E-commerce Database Assistant with full admin access to your entire database. I can help you query any data, analyze business metrics, track orders and shipments, manage inventory, review customer behavior, and provide comprehensive insights across all tables in your e-commerce platform!"
"""
        
        prompt = f"""
You are an AI E-commerce Database Assistant with ADMIN-level access to the entire database.

DATABASE SCHEMA & RELATIONSHIPS:

1. **product** (Main products table)
   - product_id (UUID, PK)
   - name, description, sku
   - price (NUMERIC), sale_price (NUMERIC), currency (CHAR(3))
   - stock (INTEGER) - available inventory
   - category_id (INTEGER) → FK to category.category_id
   - photos (TEXT[]), colors (JSONB), sizes (TEXT[])
   - materials, care, product_url, featured (BOOLEAN)
   - category_name (TEXT) - denormalized for quick access
   - created_at, updated_at, is_active (BOOLEAN)
   - embedding (VECTOR) - for semantic search

2. **category** (Product categories)
   - category_id (INTEGER, PK)
   - name (VARCHAR), type (TEXT)
   - parent_category_id (INTEGER, FK) - self-referencing for hierarchy
   - img_url, created_at, updated_at
   - embedding (VECTOR)

3. **"user"** (Customer/user accounts - QUOTED, reserved word!)
   - user_id (VARCHAR, PK) - NOT UUID!
   - email (TEXT, UNIQUE) - **CRITICAL: Used to join with order.user_id**
   - full_name, phone, address, city, country
   - date_of_birth (DATE), job, gender
   - role (TEXT, default 'user') - 'user', 'admin', 'visitor'
   - role_id (INTEGER) → FK to roles_bk.role_id
   - uid, photo_url, provider (for OAuth)
   - created_at, updated_at, is_active (BOOLEAN)
   - embedding (VECTOR)

4. **"order"** (Customer orders - QUOTED, reserved word!)
   - order_id (UUID, PK)
   - user_id (VARCHAR) - **CRITICAL: Contains EMAIL/TEXT, NOT UUID!**
   - **JOIN RULE: "user".email = "order".user_id** (NOT user_id = user_id!)
   - status (TEXT) - 'pending', 'processing', 'shipped', 'delivered', 'cancelled'
   - order_total (NUMERIC) - **total amount including all charges**
   - subtotal, tax, shipping_charges, discount (NUMERIC)
   - currency (CHAR(3), default 'USD')
   - shipping_info (JSONB) - address, method, etc.
   - created_at, updated_at
   - embedding (VECTOR)

5. **order_item** (Items in each order)
   - order_item_id (UUID, PK)
   - order_id (UUID) → FK to "order".order_id
   - product_id (UUID) → FK to product.product_id
   - quantity (INTEGER), unit_price (NUMERIC), total_price (NUMERIC)
   - created_at, updated_at
   - embedding (VECTOR)
   - **Relationship: order → order_item (1:many), product → order_item (1:many)**

6. **payment** (Payment transactions)
   - payment_id (UUID, PK)
   - order_id (UUID) → FK to "order".order_id
   - amount (NUMERIC) - payment amount
   - method (VARCHAR) - 'credit_card', 'paypal', 'bank_transfer', etc.
   - status (VARCHAR) - 'pending', 'completed', 'failed', 'refunded'
   - paid_at (TIMESTAMP)
   - created_at, updated_at
   - embedding (VECTOR)
   - **Relationship: order → payment (1:1 or 1:many)**

7. **shipment** (Shipping/delivery tracking)
   - shipment_id (UUID, PK)
   - order_id (UUID) → FK to "order".order_id
   - tracking_number (VARCHAR)
   - status (VARCHAR) - 'pending', 'in_transit', 'delivered', 'failed'
   - carrier_id (UUID) - carrier/driver reference
   - shipped_at, delivered_at (TIMESTAMP)
   - created_at, updated_at
   - embedding (VECTOR)
   - **Relationship: order → shipment (1:1 or 1:many)**

8. **product_review** (Customer product reviews)
   - product_review_id (UUID, PK)
   - product_id (UUID) → FK to product.product_id
   - user_id (VARCHAR) → FK to "user".user_id
   - rating (INTEGER, 1-5), title, comment (TEXT)
   - created_at, updated_at
   - embedding (VECTOR)
   - **Relationship: product → review (1:many), user → review (1:many)**

9. **cart** (Shopping carts)
   - cart_id (INTEGER, PK)
   - user_id (VARCHAR) → FK to "user".user_id
   - status (cart_status) - 'active', 'abandoned', 'checked_out'
   - total_price (NUMERIC)
   - created_at, updated_at
   - embedding (VECTOR)

10. **cart_item** (Items in shopping carts)
    - cart_item_id (INTEGER, PK)
    - cart_id (INTEGER) → FK to cart.cart_id
    - product_id (UUID) → FK to product.product_id
    - quantity (INTEGER), unit_price, total_price (NUMERIC)
    - created_at, updated_at
    - embedding (VECTOR)

11. **inventory** (Product inventory tracking)
    - inventory_id (UUID, PK)
    - product_id (UUID) → FK to product.product_id
    - warehouse_id (UUID)
    - quantity (INTEGER) - available stock
    - last_updated (TIMESTAMP)
    - embedding (VECTOR)

12. **coupon** (Discount coupons)
    - coupon_id (UUID, PK)
    - code (VARCHAR, UNIQUE) - coupon code
    - discount_type (VARCHAR) - 'percent' or 'amount'
    - value (NUMERIC), amount (NUMERIC)
    - valid_from, valid_to (TIMESTAMP)
    - usage_count (INTEGER)
    - created_at, updated_at
    - embedding (VECTOR)

13. **event** (User activity tracking)
    - event_id (UUID, PK)
    - user_id (UUID), session_id (VARCHAR)
    - event_type (VARCHAR) - 'page_view', 'product_view', 'add_to_cart', etc.
    - page_url, product_id (TEXT)
    - metadata (JSONB) - additional event data
    - ts (TIMESTAMP)
    - embedding (VECTOR)

14. **chat_history** (Conversation history)
    - id (INTEGER, PK)
    - session_id (TEXT), customer_id (UUID)
    - user_message, bot_response (TEXT)
    - timestamp (TIMESTAMP)
    - metadata (JSONB)

CRITICAL JOIN RULES:
- **user ↔ order**: "user".email = "order".user_id (order.user_id stores EMAIL!)
- **order ↔ order_item**: "order".order_id = order_item.order_id
- **order ↔ payment**: "order".order_id = payment.order_id
- **order ↔ shipment**: "order".order_id = shipment.order_id
- **product ↔ order_item**: product.product_id = order_item.product_id
- **product ↔ category**: product.category_id = category.category_id
- **Always QUOTE reserved words**: "user", "order"

ANALYTICS QUERIES YOU CAN ANSWER:
- Revenue: SUM(order_total) from "order" WHERE status != 'cancelled'
- Monthly revenue: Filter by DATE_TRUNC('month', created_at)
- Order counts: COUNT(*) from "order" grouped by status
- Top products: JOIN order_item with product, GROUP BY product, ORDER BY SUM(quantity)
- Customer analytics: COUNT orders per user, total spending, etc.
- Inventory levels: product.stock or inventory.quantity
- Payment status: COUNT(*) from payment GROUP BY status
- Shipment tracking: Join shipment with order for delivery status

{intro_message}

FORMATTING RULES:
- Use **bold** for metrics, IDs, key values
- Use bullet points (•/-) for lists
- Use numbered lists (1., 2., 3.) for rankings
- Format prices: **$1,234.56**
- Use ⭐ for ratings
- Tables for multiple entries
- Line breaks for readability

PRODUCT FORMAT (JSON per line):
{{"type":"product","name":"Product Name","price":29.99,"sale_price":19.99,"image":"https://...","url":"https://...","stock":50,"colors":[],"sizes":["S","M","L"]}}

ORDER FORMAT (JSON per line):
{{"type":"order","order_id":"abc-123","status":"Delivered","total":161.64,"currency":"USD","placed_date":"2025-10-15","url":"https://hackathon-478514.web.app/order/{{order_id}}","items_count":2,"item_names":["Product 1","Product 2"]}}

User Query: {query}

Retrieved Data:
{context}

Provide accurate, data-driven answer with rich formatting:
"""
        
        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return f"I found some information but couldn't generate a summary. Here is the raw data:\n\n{context}"

    def get_analytics_data(self, query_lower: str) -> Dict[str, Any]:
        """Fetch analytics data for revenue, orders, etc."""
        analytics = {}
        conn = get_db_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Revenue queries
                if any(word in query_lower for word in ['revenue', 'sales', 'total amount', 'earnings']):
                    # This month's revenue
                    cur.execute("""
                        SELECT 
                            COALESCE(SUM(order_total), 0) as total_revenue,
                            COUNT(*) as order_count
                        FROM "order"
                        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                            AND status != 'cancelled'
                    """)
                    monthly = cur.fetchone()
                    analytics['monthly_revenue'] = monthly
                    
                    # Total revenue (all time)
                    cur.execute("""
                        SELECT 
                            COALESCE(SUM(order_total), 0) as total_revenue,
                            COUNT(*) as total_orders
                        FROM "order"
                        WHERE status != 'cancelled'
                    """)
                    total = cur.fetchone()
                    analytics['total_revenue'] = total
                    
                    # Revenue by status
                    cur.execute("""
                        SELECT 
                            status,
                            COUNT(*) as count,
                            COALESCE(SUM(order_total), 0) as revenue
                        FROM "order"
                        GROUP BY status
                        ORDER BY revenue DESC
                    """)
                    by_status = cur.fetchall()
                    analytics['revenue_by_status'] = by_status
                
                # Order analytics
                if any(word in query_lower for word in ['order', 'orders', 'purchase']):
                    cur.execute("""
                        SELECT 
                            status,
                            COUNT(*) as count
                        FROM "order"
                        GROUP BY status
                        ORDER BY count DESC
                    """)
                    order_status = cur.fetchall()
                    analytics['order_status_breakdown'] = order_status
                
                # Product analytics
                if any(word in query_lower for word in ['top product', 'best selling', 'popular product']):
                    cur.execute("""
                        SELECT 
                            p.product_id,
                            p.name,
                            p.price,
                            p.sale_price,
                            COUNT(oi.order_item_id) as times_ordered,
                            SUM(oi.quantity) as total_quantity,
                            SUM(oi.total_price) as total_revenue
                        FROM product p
                        JOIN order_item oi ON p.product_id = oi.product_id
                        GROUP BY p.product_id, p.name, p.price, p.sale_price
                        ORDER BY total_quantity DESC
                        LIMIT 10
                    """)
                    top_products = cur.fetchall()
                    analytics['top_products'] = top_products
                
                # Customer analytics
                if any(word in query_lower for word in ['customer', 'user', 'top customer', 'best customer']):
                    cur.execute("""
                        SELECT 
                            u.user_id,
                            u.email,
                            u.full_name,
                            COUNT(o.order_id) as order_count,
                            COALESCE(SUM(o.order_total), 0) as total_spent
                        FROM "user" u
                        JOIN "order" o ON u.email = o.user_id
                        WHERE o.status != 'cancelled'
                        GROUP BY u.user_id, u.email, u.full_name
                        ORDER BY total_spent DESC
                        LIMIT 10
                    """)
                    top_customers = cur.fetchall()
                    analytics['top_customers'] = top_customers
                
                # Payment analytics
                if any(word in query_lower for word in ['payment', 'paid', 'transaction']):
                    cur.execute("""
                        SELECT 
                            status,
                            method,
                            COUNT(*) as count,
                            COALESCE(SUM(amount), 0) as total_amount
                        FROM payment
                        GROUP BY status, method
                        ORDER BY total_amount DESC
                    """)
                    payment_stats = cur.fetchall()
                    analytics['payment_stats'] = payment_stats
                
        except Exception as e:
            logger.error(f"Error fetching analytics: {e}")
            analytics['error'] = str(e)
        finally:
            conn.close()
        
        return analytics

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
            # First, check if this is an analytics query
            is_analytics_query = any(word in query_lower for word in [
                'revenue', 'sales', 'total', 'earnings', 'top product', 'best selling',
                'popular', 'top customer', 'best customer', 'how many', 'count'
            ])
            
            if is_analytics_query and not is_intro_query:
                # Fetch analytics data directly
                analytics_data = self.get_analytics_data(query_lower)
                if analytics_data:
                    context_parts.append(f"Analytics Data: {analytics_data}")
                    debug_info['data_accessed'].append('analytics')
            
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
            if any(word in query_lower for word in ['payment', 'paid', 'transaction method']):
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
            if not tables_to_search and not is_intro_query and not is_analytics_query:
                tables_to_search = ['product', 'order', 'user']
                debug_info['data_accessed'].append('general_search')
            
            # Perform semantic search using the rewritten query
            if tables_to_search:
                search_results = self.semantic_search(rewritten_query, tables_to_search, limit=8)
                if search_results:
                    context_parts.append(f"Relevant Results: {search_results}")
                    debug_info['search_results_count'] = len(search_results)
            
            # Add general stats if needed and no other data was found
            if not context_parts and not is_intro_query:
                conn = get_db_connection()
                try:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            SELECT 
                                (SELECT COUNT(*) FROM "user") as total_users,
                                (SELECT COUNT(*) FROM product) as total_products,
                                (SELECT COUNT(*) FROM "order") as total_orders,
                                (SELECT COALESCE(SUM(order_total), 0) FROM "order" WHERE status != 'cancelled') as total_revenue
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
