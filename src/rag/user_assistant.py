import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from ..config import Settings

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
    
    def get_db_connection(self):
        return psycopg2.connect(
            host=self.settings.DB_HOST,
            port=self.settings.DB_PORT,
            user=self.settings.DB_USER,
            password=self.settings.DB_PASSWORD,
            dbname=self.settings.DB_NAME
        )
    
    def semantic_search(self, query: str, tables: List[str] = None, user_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search across specified tables using pgvector
        For users: products, product_reviews, categories, and user's own orders
        """
        if not self.settings.GOOGLE_API_KEY:
            logger.warning("Cannot perform semantic search without GOOGLE_API_KEY")
            return []

        # Users can access products, reviews, categories, and their own orders
        allowed_tables = ['products', 'product_review', 'category', 'orders', 'shipments']
        tables_to_search = tables if tables else ['products', 'product_review']
        tables_to_search = [t for t in tables_to_search if t in allowed_tables]

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
                        if table == 'products':
                            sql = """
                                SELECT 'products' as _source_table, 
                                       product_id, name, description, price, sale_price, 
                                       stock, category_name, colors, sizes, materials, product_url,
                                       embedding <=> %s::vector as distance 
                                FROM products
                                WHERE embedding IS NOT NULL AND is_active = true
                                ORDER BY distance ASC LIMIT %s
                            """
                            cur.execute(sql, [query_embedding, limit])
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
                        elif table == 'orders' and user_id:
                            # Only fetch user's own orders
                            sql = """
                                SELECT 'orders' as _source_table,
                                       o.order_id, o.status, o.order_total, o.currency, 
                                       o.created_at, o.subtotal, o.tax, o.shipping_charges, o.discount,
                                       o.embedding <=> %s::vector as distance
                                FROM orders o
                                WHERE o.user_id = %s AND o.embedding IS NOT NULL
                                ORDER BY distance ASC LIMIT %s
                            """
                            cur.execute(sql, [query_embedding, user_id, limit])
                        elif table == 'shipments' and user_id:
                            # Only fetch shipments for user's orders
                            sql = """
                                SELECT 'shipments' as _source_table,
                                       s.tracking_number, s.carrier, s.status, s.shipped_at, s.delivered_at,
                                       o.order_id,
                                       s.embedding <=> %s::vector as distance
                                FROM shipments s
                                JOIN orders o ON s.order_id = o.order_id
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
When users ask who you are or about yourself, introduce yourself with warmth and humor:
"Well hello there, valued customer! 🌟 So glad you're back! I'm your personal shopping buddy - think of me as that friend who always knows where the good stuff is AND remembers your birthday! 🎂

Here's what I can do for you:
📦 **Your Orders** - Track 'em, check 'em, obsessively refresh the status (no judgment, we've all been there!)
🛍️ **Products** - Help you find your next favorite thing
⭐ **Reviews** - The tea on what other shoppers think ☕
🏷️ **Categories** - Your personal tour guide through our collections

So, what can I help you with today? Tracking a package? Finding something new to love? I'm all ears! 👂😊"
"""
        
        prompt = f"""
You are a fun, enthusiastic PERSONAL SALES ASSISTANT for a logged-in customer. You're like their favorite shop employee who remembers them and genuinely cares about their experience.

YOUR PERSONALITY:
🎭 Humorous - Use light jokes, playful language, and fun emojis
🌟 Enthusiastic - Get excited about products and helping YOUR customer
🤝 Proactive - Always ask follow-up questions and offer personalized suggestions
💬 Conversational - Chat like a friendly salesperson who knows them
🎯 Helpful - Balance between sales and genuine assistance
💝 Personal - They have an account, make them feel valued!

WHAT YOU CAN ACCESS:
✅ Customer's own orders (status, items, history) - Make them feel taken care of!
✅ Order shipments and tracking - Help ease their "where's my package" anxiety 😄
✅ Products (names, descriptions, prices, stock, colors, sizes, materials, product_url)
✅ Product reviews and ratings
✅ Product categories

WHAT YOU CANNOT ACCESS:
❌ Other customers' data (privacy first!)
❌ Admin-level stuff (you're sales, not management 😉)
❌ Payment details (security reasons)

{intro_message}

HOW TO RESPOND:
1. **Be Their Favorite Salesperson** - Personalized, warm, remembers they're a valued customer
2. **Include Product Links** - When mentioning products, always include the product URL
3. **Ask Engaging Follow-up Questions** - End with questions like:
   - "Happy with this info, or need me to dig deeper? 🔍"
   - "Does this help? What else can I find for you?"
   - "Is this what you were looking for, or should we explore more options?"
   - "Anything else catching your eye today? 👀"
   - "Need any other details? I'm here for you!"
   - "What do you think - love it or should we keep looking?"
4. **Be Proactive** - Suggest products based on their history, mention what's new
5. **Use Humor** - Light jokes, relatable shopping moments, playful tone
6. **Show You Care** - About their orders, their satisfaction, their experience

FOR ORDERS:
- Be reassuring about delivery
- Celebrate with them when things arrive!
- Be empathetic if there are delays

FOR PRODUCTS:
- Get excited about cool items
- Share why other customers love them
- Suggest complementary products

FORMATTING:
- 🏷️ Prices: "$29.99" or "~~$39.99~~ **$29.99** (Nice savings!)"
- 🔗 Include product links when available
- ⭐ Ratings: "⭐ 4.8/5 - Customers are obsessed!"
- 📦 Order status with friendly commentary
- Use emojis to keep it fun
- Be conversational, not corporate

EXAMPLE TONE:
"Great news! 🎉 Your order is on its way - it shipped yesterday and should arrive by Friday! I know waiting is the hardest part, but trust me, it'll be worth it! 📦✨

While you wait, I noticed we just got some new arrivals that might be your style... want me to show you what's hot this week? No pressure, just thought you might want first dibs! 😉"

Context from database:
{context}

Customer's Question: {query}

Respond as their favorite, enthusiastic sales assistant. Be fun, personal, include product links when relevant, and always end with an engaging follow-up question:
"""
        
        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return context if context else "I'm sorry, I couldn't process your request. Please try again."
    
    def process_query(self, query: str, user_id: Optional[str] = None, 
                     return_debug: bool = False) -> Any:
        """Process user query with access to own orders + products/reviews
        
        Args:
            query: User's question
            user_id: The authenticated user's ID (for accessing their own orders)
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
            'query_type': 'user_query',
            'user_id': user_id,
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
                tables_to_search.append('orders')
                tables_to_search.append('shipments')
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
                tables_to_search.append('products')
                debug_info['data_accessed'].append('products')
            
            # If no specific table matched, search products by default (unless intro query)
            if not tables_to_search and not is_intro_query:
                tables_to_search = ['products', 'product_review']
                if user_id:
                    tables_to_search.append('orders')
                debug_info['data_accessed'].append('general_search')
            
            # Perform semantic search
            if tables_to_search:
                search_results = self.semantic_search(query, tables_to_search, user_id=user_id, limit=8)
                if search_results:
                    context_parts.append(f"Relevant Results: {search_results}")
                    debug_info['search_results_count'] = len(search_results)
            
            # Add general stats if needed
            if not context_parts and not is_intro_query:
                conn = self.get_db_connection()
                try:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("SELECT COUNT(*) as total_products FROM products WHERE is_active = true")
                        stats = cur.fetchone()
                        context_parts.append(f"We have {stats['total_products']} products available.")
                        
                        if user_id:
                            cur.execute("SELECT COUNT(*) as order_count FROM orders WHERE user_id = %s", (user_id,))
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
        
        # Generate response with LLM
        response = self.generate_llm_response(query, context, is_intro_query=is_intro_query)
        
        if return_debug:
            return response, debug_info
        return response
