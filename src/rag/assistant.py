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
                    SELECT * FROM orders 
                    WHERE customer_id = %s 
                    ORDER BY order_datetime DESC
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
                    SELECT * FROM orders 
                    WHERE LOWER(order_priority) = 'high' 
                    ORDER BY order_datetime DESC 
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
            response += (f"- {product['product_title']}\n"
                       f"  Rating: {float(product['rating']):.1f}\n"
                       f"  Price: ${float(product['price']):.2f}\n"
                       f"  Description: {product['description'][:200]}...\n\n")
        return response

    def generate_llm_response(self, query: str, context: str) -> str:
        """Generate natural language response using Gemini"""
        if not self.llm:
            return context
        
        prompt = f"""
        You are a friendly E-commerce Shopping Assistant for an online retail platform. Your personality:
        - Helpful, knowledgeable, and enthusiastic about products
        - Professional yet conversational
        - Focus on providing value to customers
        
        When users ask who you are or about yourself, introduce yourself as:
        "I'm your E-commerce Shopping Assistant, powered by advanced AI to help you find the perfect products and manage your orders. I can search through our product catalog, check order status, and provide personalized recommendations!"
        
        IMPORTANT FORMATTING RULES:
        - Use **bold** for product names, prices, and important information
        - Use bullet points with • or - for lists
        - Use numbered lists (1., 2., 3.) for step-by-step instructions
        - Use line breaks (two enters) to separate paragraphs for better readability
        - Format prices with $ symbol
        - Highlight ratings with ⭐ symbol when mentioning them
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
    
    def semantic_search(self, query: str, min_rating: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search with rating filter using pgvector
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
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Base query
                sql = """
                    SELECT *, embedding <=> %s::vector as distance 
                    FROM products 
                """
                params = [query_embedding]
                
                # Add rating filter
                if min_rating is not None:
                    sql += " WHERE rating >= %s"
                    params.append(min_rating)
                
                # Order by distance (similarity)
                sql += " ORDER BY distance ASC LIMIT 5"
                
                cur.execute(sql, params)
                return cur.fetchall()
                
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def classify_intent(self, query: str) -> str:
        """Classify user query intent"""
        if not self.llm:
            return "SEMANTIC_SEARCH"
            
        prompt = f"""
        Classify the following user query into one of these categories:
        1. SQL_QUERY: Questions about specific data, statistics, aggregations, orders, or filtering products by strict criteria (price, rating, category).
        2. SEMANTIC_SEARCH: Vague or descriptive product searches, looking for recommendations based on features or description.
        3. GENERAL_CHAT: Greetings, pleasantries, or questions unrelated to the e-commerce data.
        
        Query: {query}
        
        Return ONLY the category name.
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
        Table: products
        - product_id (TEXT)
        - product_title (TEXT)
        - description (TEXT)
        - category (TEXT)
        - price (FLOAT)
        - rating (FLOAT)
        - rating_count (INTEGER)
        - store (TEXT)
        
        Table: orders
        - order_id (TEXT)
        - order_datetime (TIMESTAMP)
        - customer_id (TEXT)
        - product (TEXT)
        - sales (FLOAT)
        - quantity (INTEGER)
        - total_amount (FLOAT)
        - profit (FLOAT)
        - shipping_cost (FLOAT)
        - order_priority (TEXT)
        """
        
        prompt = f"""
        You are a PostgreSQL expert. Generate a valid SQL query to answer the user's question based on the schema below.
        
        Schema:
        {schema}
        
        Context:
        - Current Customer ID: {customer_id if customer_id else 'Not set'}
        - If the user asks about "my orders" or "latest order", use the customer_id.
        - If customer_id is not set and the query requires it, return "NEED_CUSTOMER_ID".
        - Use ILIKE for text comparisons.
        - Limit results to 5 unless specified otherwise.
        - Return ONLY the SQL query, no markdown, no explanation.
        
        User Question: {query}
        """
        
        try:
            response = self.llm.generate_content(prompt)
            sql = response.text.strip().replace('```sql', '').replace('```', '').strip()
            return sql
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return ""

    def execute_sql(self, sql: str) -> Any:
        """Execute SQL query safely"""
        if not sql or "NEED_CUSTOMER_ID" in sql:
            return "Please provide your Customer ID first (e.g., 'set customer 12345')."
            
        # Basic safety check
        if not sql.upper().startswith("SELECT"):
            return "Sorry, I can only perform read operations."
            
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

    def process_query(self, query: str, customer_id: Optional[int] = None) -> str:
        """Process user query with intelligent routing"""
        intent = self.classify_intent(query)
        logger.info(f"Query Intent: {intent}")
        
        context = ""
        
        if intent == "GENERAL_CHAT":
            return self.generate_llm_response(query, "User is engaging in general conversation.")
            
        elif intent == "SQL_QUERY":
            sql = self.generate_sql_query(query, customer_id)
            if sql == "NEED_CUSTOMER_ID":
                return "Could you please provide your Customer ID first? (Type 'set customer <id>')"
            
            logger.info(f"Generated SQL: {sql}")
            results = self.execute_sql(sql)
            context = f"SQL Query Results: {results}"
            
        else: # SEMANTIC_SEARCH
            # Extract rating requirement if present (legacy logic kept for hybrid approach)
            min_rating = None
            if 'above' in query and any(char.isdigit() for char in query):
                try:
                    rating_idx = query.find('above') + 5
                    rating_str = ''.join(c for c in query[rating_idx:] if c.isdigit() or c == '.')
                    min_rating = float(rating_str)
                except ValueError:
                    pass
            
            products = self.semantic_search(query, min_rating=min_rating)
            context = self.format_product_results(products)
            
        return self.generate_llm_response(query, context)
