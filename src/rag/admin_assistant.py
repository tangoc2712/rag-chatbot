import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from ..config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECommerceRAG:
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

    def get_customer_orders(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get orders for a specific customer"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM "order" 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC
                """, (str(customer_id),))
                return cur.fetchall()
        finally:
            conn.close()
    
    def get_high_priority_orders(self) -> List[Dict[str, Any]]:
        """Get high priority orders"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM "order" 
                    WHERE status = 'pending' 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                return cur.fetchall()
        finally:
            conn.close()
    
    def format_single_order(self, order: Dict[str, Any]) -> str:
        """Format single order details"""
        return (f"Order Date: {order['order_datetime']}\n"
                f"Product: {order['product']}\n"
                f"Total Amount: ${float(order['sales']):.2f}\n"
                f"Shipping Cost: ${float(order['shipping_cost']):.2f}\n"
                f"Priority: {order['order_priority']}")
    
    def format_high_priority_orders(self, orders: List[Dict[str, Any]]) -> str:
        """Format high priority orders list"""
        if not orders:
            return "No high priority orders found."
        
        response = "High Priority Orders:\n"
        for i, order in enumerate(orders, 1):
            response += (
                f"{i}. Date: {order['order_datetime']}, "
                f"Product: {order['product']}, "
                f"Amount: ${float(order['sales']):.2f}, "
                f"Customer ID: {order['customer_id']}\n"
            )
        return response
    
    def format_product_results(self, products: List[Dict[str, Any]]) -> str:
        """Format product results"""
        if not products:
            return "No products found."
        
        response = "Found Products:\n"
        for product in products:
            # Handle both old schema (product_title) and new schema (name)
            name = product.get('product_title') or product.get('name', 'Unknown')
            rating = product.get('rating', 0)
            price = product.get('price', 0)
            description = product.get('description', '')
            
            response += f"- {name}\n"
            if rating:
                response += f"  Rating: {float(rating):.1f}\n"
            response += f"  Price: ${float(price):.2f}\n"
            if description:
                response += f"  Description: {description[:200]}...\n\n"
            else:
                response += "\n"
        return response
    
    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format multi-table search results"""
        if not results:
            return "No results found."
        
        response = "Found Results:\n\n"
        for item in results:
            source_table = item.get('_source_table', 'unknown')
            response += f"[{source_table.upper()}]\n"
            
            if source_table == 'products':
                response += f"- {item.get('name', 'Unknown')}\n"
                if item.get('price'):
                    response += f"  Price: ${float(item['price']):.2f}\n"
                if item.get('description'):
                    response += f"  {item['description'][:150]}...\n"
            elif source_table == 'users':
                response += f"- {item.get('full_name', 'Unknown')}\n"
                response += f"  Email: {item.get('email', 'N/A')}\n"
                if item.get('job'):
                    response += f"  Job: {item['job']}\n"
            elif source_table == 'orders':
                response += f"- Order #{item.get('order_id', 'N/A')}\n"
                response += f"  Date: {item.get('order_date', 'N/A')}\n"
                response += f"  Status: {item.get('status', 'N/A')}\n"
                if item.get('total_amount'):
                    response += f"  Total: ${float(item['total_amount']):.2f}\n"
            elif source_table == 'product_reviews':
                response += f"- Rating: {item.get('rating', 'N/A')}/5\n"
                response += f"  {item.get('review_text', '')[:150]}...\n"
            elif source_table == 'coupons':
                response += f"- Code: {item.get('coupon_code', 'N/A')}\n"
                response += f"  Discount: {item.get('discount_value', 0)}\n"
                response += f"  Min Purchase: ${item.get('min_purchase_amount', 0):.2f}\n"
            elif source_table == 'shipments':
                response += f"- Tracking: {item.get('tracking_number', 'N/A')}\n"
                response += f"  Carrier: {item.get('carrier', 'N/A')}\n"
                response += f"  Status: {item.get('status', 'N/A')}\n"
            else:
                # Generic formatting for other tables
                for key, value in item.items():
                    if key not in ['embedding', 'distance', '_source_table']:
                        response += f"  {key}: {value}\n"
            
            response += "\n"
        
        return response

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
    
    def semantic_search(self, query: str, min_rating: Optional[float] = None, 
                       table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search across multiple tables using pgvector
        Supports: products, users, orders, categories, carts, cart_items, coupons, 
                 events, inventory, order_items, payments, product_reviews, roles, shipments
        """
        if not self.settings.GOOGLE_API_KEY:
            logger.warning("Cannot perform semantic search without GOOGLE_API_KEY")
            return []

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
            
            # Determine which tables to search
            tables_to_search = []
            if table_name:
                tables_to_search = [table_name]
            else:
                # Auto-detect relevant tables based on query keywords
                query_lower = query.lower()
                if any(word in query_lower for word in ['product', 'item', 'buy', 'purchase', 'price', 'rating']):
                    tables_to_search.append('products')
                if any(word in query_lower for word in ['user', 'customer', 'profile', 'account']):
                    tables_to_search.append('users')
                if any(word in query_lower for word in ['order', 'purchase history', 'bought']):
                    tables_to_search.append('orders')
                if any(word in query_lower for word in ['review', 'comment', 'feedback', 'rating']):
                    tables_to_search.append('product_reviews')
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
                    tables_to_search.append('categories')
                
                # Default to products if no match
                if not tables_to_search:
                    tables_to_search = ['products']
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for table in tables_to_search:
                    try:
                        # Build table-specific query
                        sql = f"""
                            SELECT '{table}' as _source_table, *, 
                                   embedding <=> %s::vector as distance 
                            FROM {table}
                            WHERE embedding IS NOT NULL
                        """
                        params = [query_embedding]
                        
                        # Add rating filter for products
                        if table == 'products' and min_rating is not None:
                            sql += " AND rating >= %s"
                            params.append(min_rating)
                        
                        sql += " ORDER BY distance ASC LIMIT 3"
                        
                        cur.execute(sql, params)
                        table_results = cur.fetchall()
                        results.extend(table_results)
                    except Exception as e:
                        logger.warning(f"Error searching table {table}: {e}")
                        continue
            
            # Sort all results by distance and limit
            results.sort(key=lambda x: x.get('distance', 999))
            return results[:5]
                
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def classify_intent(self, query: str) -> str:
        """Classify user query intent for admin database queries"""
        if not self.llm:
            return "SEMANTIC_SEARCH"
            
        prompt = f"""
        You are classifying admin database queries. Classify the following query into one of these categories:
        
        1. SQL_QUERY: Analytical questions, data queries, statistics, aggregations, counting, filtering, or any question that requires querying structured database tables (users, orders, products, payments, shipments, inventory, reviews, etc.)
           Examples: "How many customers?", "Show top products", "Total revenue", "List pending orders", "Who are the users?", "Customer demographics"
        
        2. SEMANTIC_SEARCH: Product searches based on descriptions, features, or semantic similarity
           Examples: "Find a blue dress", "Show me laptops for gaming", "Products similar to..."
        
        3. GENERAL_CHAT: Greetings, small talk, questions about the assistant itself
           Examples: "Hello", "Who are you?", "What can you do?"
        
        Query: {query}
        
        Return ONLY the category name (SQL_QUERY, SEMANTIC_SEARCH, or GENERAL_CHAT).
        """
        try:
            response = self.llm.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return "SEMANTIC_SEARCH"

    def generate_sql_query(self, query: str, customer_id: Optional[int] = None) -> str:
        """Generate SQL query from natural language"""
        schema = """
        === E-COMMERCE DATABASE SCHEMA ===
        
        CORE TABLES:
        
        1. product (Product Catalog)
           - product_id (UUID, PK)
           - name (TEXT) - Product name
           - description (TEXT) - Product description
           - price (NUMERIC) - Current price
           - sale_price (NUMERIC) - Discounted price if on sale
           - sku (TEXT, UNIQUE) - Stock keeping unit
           - category_id (INTEGER, FK → category.category_id)
           - category_name (TEXT) - Denormalized category name
           - stock (INTEGER) - Available quantity
           - photos (TEXT[]) - Array of photo URLs
           - colors (JSONB) - Available colors
           - sizes (TEXT[]) - Available sizes
           - materials (TEXT) - Material information
           - care (TEXT) - Care instructions
           - featured (BOOLEAN) - Is featured product
           - is_active (BOOLEAN) - Is currently active
           - currency (CHAR(3)) - Currency code (USD)
           - created_at, updated_at (TIMESTAMP)
        
        2. category (Product Categories - Hierarchical)
           - category_id (INTEGER, PK)
           - name (VARCHAR(255)) - Category name
           - parent_category_id (INTEGER, FK → category.category_id, NULLABLE) - Self-referencing for hierarchy
           - type (TEXT) - Category type
           - created_at, updated_at (TIMESTAMP)
        
        3. "user" (Customer Accounts) **RESERVED WORD - ALWAYS QUOTE**
           - user_id (UUID, PK) **WARNING: DO NOT use for order joins!**
           - email (TEXT, UNIQUE) **CRITICAL: Use this to join with "order".user_id**
           - uid (TEXT, UNIQUE) - External user ID
           - full_name (TEXT) - Customer full name
           - phone (TEXT) - Phone number
           - address (TEXT) - Delivery address
           - date_of_birth (DATE) - Birthday
           - job (TEXT) - Occupation
           - gender (TEXT) - Gender
           - role_id (INTEGER, FK → roles_bk.role_id)
           - role (TEXT, default 'user') - User role
           - is_active (BOOLEAN) - Account status
           - photo_url (TEXT) - Profile photo
           - provider (TEXT) - Auth provider
           - password_hash (TEXT) - Hashed password
           - created_at, updated_at (TIMESTAMP)
        
        4. "order" (Customer Orders) **RESERVED WORD - ALWAYS QUOTE**
           - order_id (UUID, PK)
           - user_id (TEXT) **CRITICAL: Contains EMAIL (not UUID)! Join: "user".email = "order".user_id**
           - status (TEXT) - Order status (pending, processing, completed, cancelled)
           - order_total (NUMERIC) - Total order amount
           - subtotal (NUMERIC) - Subtotal before taxes
           - tax (NUMERIC) - Tax amount
           - discount (NUMERIC) - Discount applied
           - shipping_charges (NUMERIC) - Shipping cost
           - currency (CHAR(3)) - Currency code
           - shipping_info (JSONB) - Shipping address and details
           - created_at, updated_at (TIMESTAMP)
        
        5. order_item (Items in Orders)
           - order_item_id (UUID, PK)
           - order_id (UUID, FK → "order".order_id)
           - product_id (UUID, FK → product.product_id)
           - quantity (INTEGER) - Item quantity
           - unit_price (NUMERIC) - Price per unit
           - total_price (NUMERIC) - quantity × unit_price
           - created_at, updated_at (TIMESTAMP)
        
        6. cart (Shopping Carts)
           - cart_id (INTEGER, PK)
           - user_id (UUID, FK → "user".user_id)
           - status (cart_status) - Cart status (active, abandoned, converted)
           - total_price (NUMERIC) - Cart total
           - created_at, updated_at (TIMESTAMP)
        
        7. cart_item (Items in Shopping Carts)
           - cart_item_id (INTEGER, PK)
           - cart_id (INTEGER, FK → cart.cart_id)
           - product_id (UUID, FK → product.product_id)
           - quantity (INTEGER) - Item quantity
           - unit_price (NUMERIC) - Price per unit
           - total_price (NUMERIC) - quantity × unit_price
           - created_at, updated_at (TIMESTAMP)
        
        8. payment (Payment Transactions)
           - payment_id (UUID, PK)
           - order_id (UUID, FK → "order".order_id)
           - amount (NUMERIC) - Payment amount
           - method (VARCHAR(50)) - Payment method (credit_card, paypal, etc.)
           - status (VARCHAR(50)) - Payment status (pending, completed, failed)
           - paid_at (TIMESTAMP) - Payment timestamp
           - created_at, updated_at (TIMESTAMP)
        
        9. shipment (Order Shipments)
           - shipment_id (UUID, PK)
           - order_id (UUID, FK → "order".order_id)
           - tracking_number (VARCHAR(255)) - Tracking number
           - status (VARCHAR(50)) - Shipment status (preparing, shipped, in_transit, delivered)
           - carrier_id (UUID, FK → "user".user_id) - Delivery carrier
           - shipped_at (TIMESTAMP) - Shipment date
           - delivered_at (TIMESTAMP) - Delivery date
           - created_at, updated_at (TIMESTAMP)
        
        10. product_review (Product Reviews & Ratings)
            - product_review_id (UUID, PK)
            - product_id (UUID, FK → product.product_id)
            - user_id (UUID, FK → "user".user_id)
            - rating (INTEGER) - 1-5 stars
            - comment (TEXT) - Review text
            - created_at, updated_at (TIMESTAMP)
        
        11. inventory (Stock Management)
            - inventory_id (UUID, PK)
            - product_id (UUID, FK → product.product_id)
            - warehouse_id (UUID) - Warehouse identifier
            - quantity (INTEGER) - Stock quantity
            - last_updated (TIMESTAMP) - Last inventory update
        
        12. coupon (Discount Coupons)
            - coupon_id (UUID, PK)
            - code (VARCHAR(100), UNIQUE) - Coupon code
            - discount_type (VARCHAR(20)) - 'percent' or 'amount'
            - value (NUMERIC) - Discount value
            - amount (NUMERIC) - Alternative discount amount
            - valid_from (TIMESTAMP) - Start date
            - valid_to (TIMESTAMP) - End date
            - usage_count (INTEGER) - Times used
            - created_at, updated_at (TIMESTAMP)
        
        13. event (User Activity Events)
            - event_id (UUID, PK)
            - user_id (UUID, FK → "user".user_id, NULLABLE)
            - session_id (VARCHAR(255)) - Session identifier
            - event_type (VARCHAR(255)) - Event type (page_view, add_to_cart, etc.)
            - metadata (JSONB) - Event metadata
            - ts (TIMESTAMP) - Event timestamp
        
        14. roles_bk (User Roles)
            - role_id (INTEGER, PK)
            - role_name (TEXT) - Role name (admin, customer, vendor)
            - is_active (BOOLEAN) - Role status
            - created_at, updated_at (TIMESTAMP)
        
        === COMMON JOIN PATTERNS ===
        
        Orders with Customer Info:
        SELECT * FROM "order" o 
        JOIN "user" u ON u.email = o.user_id
        
        Orders with Items and Products:
        SELECT * FROM "order" o
        JOIN order_item oi ON oi.order_id = o.order_id
        JOIN product p ON p.product_id = oi.product_id
        
        Orders with Payment Status:
        SELECT * FROM "order" o
        JOIN payment p ON p.order_id = o.order_id
        
        Orders with Shipment Tracking:
        SELECT * FROM "order" o
        JOIN shipment s ON s.order_id = o.order_id
        
        Products with Reviews:
        SELECT * FROM product p
        LEFT JOIN product_review pr ON pr.product_id = p.product_id
        
        Products with Inventory:
        SELECT * FROM product p
        LEFT JOIN inventory i ON i.product_id = p.product_id
        
        Products by Category:
        SELECT * FROM product p
        JOIN category c ON c.category_id = p.category_id
        
        User Activity:
        SELECT * FROM "user" u
        LEFT JOIN "order" o ON o.user_id = u.email
        LEFT JOIN event e ON e.user_id = u.user_id
        """
        
        prompt = f"""
        You are a PostgreSQL expert generating SQL queries for an e-commerce analytics platform.
        
        SCHEMA:
        {schema}
        
        CRITICAL RULES:
        1. **Reserved Words**: ALWAYS quote "user" and "order" tables
           ✓ Correct: SELECT * FROM "user" u JOIN "order" o
           ✗ Wrong: SELECT * FROM user u JOIN order o
        
        2. **User-Order Join**: "order".user_id contains EMAIL (TEXT), NOT UUID
           ✓ Correct: "user".email = "order".user_id
           ✗ Wrong: "user".user_id = "order".user_id
        
        3. **Table Relationships**: Use proper foreign keys
           - order_item.order_id → "order".order_id
           - order_item.product_id → product.product_id
           - payment.order_id → "order".order_id
           - shipment.order_id → "order".order_id
           - cart.user_id → "user".user_id (UUID, correct!)
           - product_review.user_id → "user".user_id (UUID, correct!)
        
        4. **Column Selection**: Be specific with column names from schema
        
        5. **Aggregations**: Use appropriate GROUP BY with COUNT, SUM, AVG, MAX, MIN
        
        6. **Ordering**: Sort by relevant columns (order_total DESC, created_at DESC, rating DESC)
        
        7. **Limiting**: Default LIMIT 10 for lists, LIMIT 5 for top/bottom queries
        
        8. **Case Sensitivity**: Use ILIKE for case-insensitive text searches
        
        9. **Date Filtering**: Use created_at, updated_at, paid_at, shipped_at as needed
        
        10. **Output Format**: Return ONLY the SQL query, no markdown, no explanations
        
        EXAMPLE QUERIES:
        
        Q: "Show top 5 orders by value"
        A: SELECT order_id, user_id, order_total, status, created_at FROM "order" ORDER BY order_total DESC LIMIT 5
        
        Q: "Which customers spent the most?"
        A: SELECT u.full_name, u.email, COUNT(o.order_id) as order_count, SUM(o.order_total) as total_spent FROM "user" u JOIN "order" o ON u.email = o.user_id GROUP BY u.user_id, u.full_name, u.email ORDER BY total_spent DESC LIMIT 10
        
        Q: "Products with best ratings"
        A: SELECT p.name, p.price, AVG(pr.rating) as avg_rating, COUNT(pr.product_review_id) as review_count FROM product p JOIN product_review pr ON pr.product_id = p.product_id GROUP BY p.product_id, p.name, p.price HAVING COUNT(pr.product_review_id) >= 3 ORDER BY avg_rating DESC LIMIT 10
        
        Q: "Orders pending shipment"
        A: SELECT o.order_id, o.order_total, o.created_at, u.full_name, u.email FROM "order" o JOIN "user" u ON u.email = o.user_id LEFT JOIN shipment s ON s.order_id = o.order_id WHERE s.shipment_id IS NULL AND o.status != 'cancelled' ORDER BY o.created_at ASC
        
        User Question: {query}
        
        Generate the SQL query:
        """
        
        try:
            response = self.llm.generate_content(prompt)
            sql = response.text.strip().replace('```sql', '').replace('```', '').strip()
            
            # CRITICAL FIX: Automatically fix wrong joins between user and order
            # Replace any variations of wrong joins with the correct one
            import re
            
            # Pattern 1: user.user_id = order.user_id or similar
            sql = re.sub(
                r'"?user"?\.user_id\s*=\s*"?order"?\.user_id',
                '"user".email = "order".user_id',
                sql,
                flags=re.IGNORECASE
            )
            
            # Pattern 2: u.user_id = o.user_id (with aliases)
            sql = re.sub(
                r'\bu\.user_id\s*=\s*o\.user_id\b',
                'u.email = o.user_id',
                sql,
                flags=re.IGNORECASE
            )
            
            # Pattern 3: ON user_id (without table prefix)
            if 'JOIN orders' in sql and 'user_id' in sql:
                sql = re.sub(
                    r'ON\s+user_id',
                    'ON users.email = orders.user_id',
                    sql,
                    flags=re.IGNORECASE
                )
            
            logger.info(f"Generated and fixed SQL: {sql}")
            return sql
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return ""

    def execute_sql(self, sql: str) -> Any:
        """Execute SQL query safely"""
        if not sql:
            return "Unable to generate SQL query for your request."
            
        # Basic safety check - only allow SELECT queries
        if not sql.upper().strip().startswith("SELECT"):
            return "Sorry, I can only perform read operations (SELECT queries)."
            
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                return cur.fetchall()
        except Exception as e:
            logger.error(f"SQL Execution Error: {e}")
            return f"Error executing query: {e}"
        finally:
            conn.close()

    def process_query(self, query: str, customer_id: Optional[int] = None, return_debug: bool = False) -> Any:
        """Process user query - use SQL for analytical queries, direct fetch for simple queries
        
        Args:
            query: User's question
            customer_id: Optional customer ID (not used in admin mode)
            return_debug: If True, return tuple of (response, debug_info)
        
        Returns:
            str or tuple: Response text, or (response, debug_info) if return_debug=True
        """
        
        query_lower = query.lower()
        
        # Check if this is an introduction/greeting query
        is_intro_query = any(word in query_lower for word in ['who are you', 'what are you', 'what can you do', 'introduce yourself', 'your capabilities'])
        
        # Check if this is an analytical query that needs SQL
        is_analytical = any(word in query_lower for word in [
            'most', 'top', 'best', 'highest', 'lowest', 'total', 'sum', 'average', 
            'count', 'how many', 'who bought', 'who purchased', 'which customer',
            'revenue', 'sales', 'statistics', 'analyze', 'compare', 'trend'
        ])
        
        context_parts = []
        debug_info = {
            'query_type': 'analytical' if is_analytical else 'simple',
            'is_intro': is_intro_query,
            'sql_query': None,
            'sql_results': None
        }
        
        # For analytical queries, use SQL generation
        if is_analytical and not is_intro_query:
            try:
                # Generate SQL query
                sql = self.generate_sql_query(query, customer_id)
                logger.info(f"Generated SQL for analytical query: {sql}")
                debug_info['sql_query'] = sql
                
                # Execute SQL
                results = self.execute_sql(sql)
                debug_info['sql_results'] = str(results)[:500]  # Limit size
                
                if isinstance(results, str):
                    # Error message from execute_sql
                    context_parts.append(results)
                else:
                    context_parts.append(f"Query Results:\n{results}")
                    context_parts.append(f"SQL Query Used: {sql}")
                    
            except Exception as e:
                logger.error(f"Error in analytical query processing: {e}")
                context_parts.append(f"Error processing analytical query: {e}")
                debug_info['error'] = str(e)
        else:
            # For simple queries, fetch relevant data directly
            try:
                conn = self.get_db_connection()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Check for customer/user queries
                    if any(word in query_lower for word in ['customer', 'user', 'profile', 'account']):
                        cur.execute("SELECT * FROM \"user\" ORDER BY created_at DESC LIMIT 10")
                        users = cur.fetchall()
                        context_parts.append(f"Users Data: {users}")
                        
                        cur.execute("SELECT COUNT(*) as total FROM \"user\"")
                        count = cur.fetchone()
                        context_parts.append(f"Total Users: {count['total']}")
                    
                    # Check for product queries
                    if any(word in query_lower for word in ['product', 'item', 'inventory', 'stock']):
                        cur.execute("SELECT * FROM product ORDER BY created_at DESC LIMIT 10")
                        products = cur.fetchall()
                        context_parts.append(f"Products Data: {products}")
                        
                        cur.execute("SELECT COUNT(*) as total FROM product")
                        count = cur.fetchone()
                        context_parts.append(f"Total Products: {count['total']}")
                    
                    # Check for order queries
                    if any(word in query_lower for word in ['order', 'purchase', 'transaction']):
                        cur.execute("SELECT * FROM \"order\" ORDER BY created_at DESC LIMIT 10")
                        orders = cur.fetchall()
                        context_parts.append(f"Orders Data: {orders}")
                        
                        cur.execute("SELECT COUNT(*) as total FROM \"order\"")
                        count = cur.fetchone()
                        context_parts.append(f"Total Orders: {count['total']}")
                    
                    # Check for payment queries
                    if any(word in query_lower for word in ['payment', 'revenue', 'sales']):
                        cur.execute("SELECT * FROM payment ORDER BY paid_at DESC LIMIT 10")
                        payments = cur.fetchall()
                        context_parts.append(f"Payments Data: {payments}")
                    
                    # Check for shipment queries
                    if any(word in query_lower for word in ['shipment', 'shipping', 'delivery']):
                        cur.execute("SELECT * FROM shipment ORDER BY shipped_at DESC LIMIT 10")
                        shipments = cur.fetchall()
                        context_parts.append(f"Shipments Data: {shipments}")
                    
                    # Check for review queries
                    if any(word in query_lower for word in ['review', 'rating', 'feedback']):
                        cur.execute("SELECT * FROM product_review ORDER BY created_at DESC LIMIT 10")
                        reviews = cur.fetchall()
                        context_parts.append(f"Reviews Data: {reviews}")
                    
                    # Check for category queries
                    if any(word in query_lower for word in ['category', 'categories']):
                        cur.execute("SELECT * FROM category LIMIT 10")
                        categories = cur.fetchall()
                        context_parts.append(f"Categories Data: {categories}")
                    
                    # Check for coupon queries
                    if any(word in query_lower for word in ['coupon', 'discount', 'promo']):
                        cur.execute("SELECT * FROM coupon WHERE valid_to >= CURRENT_TIMESTAMP LIMIT 10")
                        coupons = cur.fetchall()
                        context_parts.append(f"Coupons Data: {coupons}")
                    
                    # If no specific context matched, fetch general statistics
                    if not context_parts and not is_intro_query:
                        cur.execute("""
                            SELECT 
                                (SELECT COUNT(*) FROM \"user\") as total_users,
                                (SELECT COUNT(*) FROM product) as total_products,
                                (SELECT COUNT(*) FROM \"order\") as total_orders
                        """)
                        stats = cur.fetchone()
                        context_parts.append(f"Database Statistics: {stats}")
                
                conn.close()
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
