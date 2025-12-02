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
            self.llm = genai.GenerativeModel('gemini-2.5-flash')
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
When users ask who you are or about yourself, introduce yourself as:
"I'm an AI E-commerce Database Assistant with full admin access to your entire database. I can help you query any data, analyze business metrics, track orders and shipments, manage inventory, review customer behavior, and provide comprehensive insights across all tables in your e-commerce platform!"
"""
        
        prompt = f"""
        You are an AI E-commerce Database Assistant with ADMIN-level access to the entire database. Your capabilities:
        - Access to ALL customer data, orders, products, and transactions across the entire platform
        - Analyze business metrics, sales trends, and customer behavior
        - Query any table in the database without restrictions
        - Provide insights on inventory, payments, shipments, and reviews
        - Help with data analysis and reporting
        
        {intro_message}
        
        IMPORTANT FORMATTING RULES:
        - Use **bold** for important metrics, names, IDs, and key information
        - Use bullet points with • or - for lists
        - Use numbered lists (1., 2., 3.) for rankings or step-by-step data
        - Use line breaks (two enters) to separate sections for better readability
        - Format prices with $ symbol
        - Highlight ratings with ⭐ symbol when mentioning them
        - Use tables format when showing multiple data entries
        - Make responses visually organized and easy to scan
        
        User Query: {query}
        
        Retrieved Data:
        {context}
        
        Answer (use rich formatting with markdown for better presentation):
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
        Table: product
        - product_id (UUID, PK)
        - name (TEXT)
        - description (TEXT)
        - price (NUMERIC)
        - category_id (INTEGER, FK)
        - sku (TEXT)
        - product_url (TEXT)
        - currency (CHAR(3))
        - is_active (BOOLEAN)
        - sale_price (NUMERIC)
        - stock (INTEGER)
        - photos (TEXT[])
        - colors (JSONB)
        - sizes (TEXT[])
        - materials (TEXT)
        - care (TEXT)
        - featured (BOOLEAN)
        - category_name (TEXT)
        - created_at, updated_at (TIMESTAMP)
        
        Table: category
        - category_id (INTEGER, PK)
        - name (VARCHAR(255))
        - parent_category_id (INTEGER, FK, nullable)
        - type (TEXT)
        - created_at, updated_at (TIMESTAMP)
        
        Table: "user" (quoted - reserved word)
        - user_id (UUID, PK) - DO NOT USE FOR JOINS WITH ORDERS
        - email (TEXT, UNIQUE) - USE THIS TO JOIN WITH order.user_id
        - full_name (TEXT)
        - phone (TEXT)
        - address (TEXT)
        - date_of_birth (DATE)
        - job (TEXT)
        - gender (TEXT)
        - role_id (INTEGER, FK)
        - is_active (BOOLEAN)
        - uid (TEXT)
        - photo_url (TEXT)
        - provider (TEXT)
        - role (TEXT, default 'user')
        - created_at, updated_at (TIMESTAMP)
        
        Table: roles_bk
        - role_id (INTEGER, PK)
        - role_name (TEXT)
        - is_active (BOOLEAN)
        - created_at, updated_at (TIMESTAMP)
        
        Table: "order" (quoted - reserved word)
        - order_id (UUID, PK)
        - user_id (TEXT) - CRITICAL: Contains EMAIL/TEXT! Join: "user".email = "order".user_id
        - status (TEXT)
        - order_total (NUMERIC)
        - currency (CHAR(3))
        - shipping_info (JSONB)
        - created_at, updated_at (TIMESTAMP)
        - subtotal, tax, discount, shipping_charges (NUMERIC)
        
        Table: order_item
        - order_item_id (UUID, PK)
        - order_id (UUID, FK)
        - product_id (UUID, FK)
        - quantity (INTEGER)
        - unit_price (NUMERIC)
        - total_price (NUMERIC)
        - created_at, updated_at (TIMESTAMP)
        
        Table: cart
        - cart_id (INTEGER, PK)
        - user_id (UUID, FK)
        - status (cart_status)
        - total_price (NUMERIC)
        - created_at, updated_at (TIMESTAMP)
        
        Table: cart_item
        - cart_item_id (INTEGER, PK)
        - cart_id (INTEGER, FK)
        - product_id (UUID, FK)
        - quantity (INTEGER)
        - unit_price (NUMERIC)
        - total_price (NUMERIC)
        - created_at, updated_at (TIMESTAMP)
        
        Table: payment
        - payment_id (UUID, PK)
        - order_id (UUID, FK)
        - amount (NUMERIC)
        - method (VARCHAR(50))
        - status (VARCHAR(50))
        - paid_at (TIMESTAMP)
        - created_at, updated_at (TIMESTAMP)
        
        Table: shipment
        - shipment_id (UUID, PK)
        - order_id (UUID, FK)
        - tracking_number (VARCHAR(255))
        - status (VARCHAR(50))
        - shipped_at (TIMESTAMP)
        - delivered_at (TIMESTAMP)
        - carrier_id (UUID, FK to user)
        - created_at, updated_at (TIMESTAMP)
        
        Table: inventory
        - inventory_id (UUID, PK)
        - product_id (UUID, FK)
        - warehouse_id (UUID)
        - quantity (INTEGER)
        - last_updated (TIMESTAMP)
        
        Table: product_review
        - product_review_id (UUID, PK)
        - product_id (UUID, FK)
        - user_id (UUID, FK)
        - rating (INTEGER, 1-5)
        - comment (TEXT)
        - created_at, updated_at (TIMESTAMP)
        
        Table: coupon
        - coupon_id (UUID, PK)
        - code (VARCHAR(100), UNIQUE)
        - discount_type (VARCHAR(20)) - 'percent' or 'amount'
        - value (NUMERIC)
        - amount (NUMERIC)
        - valid_from (TIMESTAMP)
        - valid_to (TIMESTAMP)
        - usage_count (INTEGER)
        - created_at, updated_at (TIMESTAMP)
        
        Table: event
        - event_id (UUID, PK)
        - user_id (UUID, FK, nullable)
        - session_id (VARCHAR(255))
        - event_type (VARCHAR(255))
        - metadata (JSONB)
        - ts (TIMESTAMP)
        
        Table: chat_history
        - id (INTEGER, PK)
        - session_id (TEXT)
        - customer_id (TEXT)
        - user_message (TEXT)
        - bot_response (TEXT)
        - timestamp (TIMESTAMP)
        - metadata (JSONB)
        """
        
        prompt = f"""
        You are a PostgreSQL expert with ADMIN access. Generate a valid SQL query to answer the user's question based on the schema below.
        
        Schema:
        {schema}
        
        Instructions:
        - You have full access to ALL data in the database (no customer_id restrictions)
        - Use appropriate JOINs to combine data from multiple tables when needed
        - CRITICAL: Tables "user" and "order" are PostgreSQL reserved words - ALWAYS quote them: "user", "order"
        - CRITICAL: When joining user and order tables, ALWAYS use: "user".email = "order".user_id
          ("order".user_id contains EMAIL/TEXT, NOT UUID!)
        - Example correct join: SELECT u.full_name, COUNT(o.order_id) FROM "user" u JOIN "order" o ON u.email = o.user_id
        - Use LIKE or ILIKE for text comparisons (case-insensitive)
        - For aggregations, use GROUP BY, COUNT, SUM, AVG as appropriate
        - Limit results to 10 unless specified otherwise
        - Order results by most relevant columns (e.g., created_at DESC, rating DESC)
        - Return ONLY the SQL query, no markdown, no explanation
        - Make sure column names and table names match the schema exactly
        - Use singular table names: product, category, "user", "order", payment, shipment, etc.
        
        User Question: {query}
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
