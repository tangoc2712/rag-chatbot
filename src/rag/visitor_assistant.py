import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from ..config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisitorECommerceRAG:
    """RAG assistant for visitors (no account) - access to products and reviews only"""
    
    def __init__(self):
        """Initialize RAG system with Database and Gemini"""
        self.settings = Settings()
        
        # Initialize Gemini
        if self.settings.GOOGLE_API_KEY:
            genai.configure(api_key=self.settings.GOOGLE_API_KEY)
            self.llm = genai.GenerativeModel('gemini-2.5-flash-lite')
            logger.info("Google Gemini LLM initialized successfully for Visitor Assistant")
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
    
    def search_products(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search products by name or description"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT product_id, name, description, price, sale_price, 
                           stock, category_name, colors, sizes, materials, photos, product_url
                    FROM products
                    WHERE (name ILIKE %s OR description ILIKE %s) AND is_active = true
                    ORDER BY featured DESC, created_at DESC
                    LIMIT %s
                """, (f'%{search_term}%', f'%{search_term}%', limit))
                return cur.fetchall()
        finally:
            conn.close()
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by ID"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT product_id, name, description, price, sale_price, 
                           stock, category_name, colors, sizes, materials, photos, care
                    FROM products
                    WHERE product_id = %s AND is_active = true
                """, (product_id,))
                return cur.fetchone()
        finally:
            conn.close()
    
    def get_product_reviews(self, product_id: str) -> List[Dict[str, Any]]:
        """Get reviews for a specific product"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT pr.rating, pr.review_text, pr.created_at
                    FROM product_review pr
                    WHERE pr.product_id = %s
                    ORDER BY pr.created_at DESC
                    LIMIT 20
                """, (product_id,))
                return cur.fetchall()
        finally:
            conn.close()
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all product categories"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM category ORDER BY name")
                return cur.fetchall()
        finally:
            conn.close()
    
    def get_featured_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get featured products"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT product_id, name, description, price, sale_price, 
                           stock, category_name, photos, product_url
                    FROM products
                    WHERE featured = true AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()
        finally:
            conn.close()
    
    def get_products_by_category(self, category_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get products by category"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT product_id, name, description, price, sale_price, stock, category_name, product_url
                    FROM products
                    WHERE category_name ILIKE %s AND is_active = true
                    ORDER BY featured DESC, created_at DESC
                    LIMIT %s
                """, (f'%{category_name}%', limit))
                return cur.fetchall()
        finally:
            conn.close()
    
    def get_top_rated_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top rated products based on reviews"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT p.product_id, p.name, p.description, p.price, p.sale_price,
                           p.category_name, AVG(pr.rating) as avg_rating, COUNT(pr.review_id) as review_count
                    FROM products p
                    LEFT JOIN product_review pr ON p.product_id::text = pr.product_id::text
                    WHERE p.is_active = true
                    GROUP BY p.product_id
                    HAVING COUNT(pr.review_id) > 0
                    ORDER BY avg_rating DESC, review_count DESC
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()
        finally:
            conn.close()

    def generate_llm_response(self, query: str, context: str, is_intro_query: bool = False) -> str:
        """Generate natural language response using Gemini"""
        if not self.llm:
            return context
        
        intro_message = ""
        if is_intro_query:
            intro_message = """
When users ask who you are or about yourself, introduce yourself with enthusiasm and humor:
"Hey there, welcome to the shop! 🎉 I'm your friendly neighborhood sales assistant (minus the spidey suit, unfortunately 🕷️). 

I'm here to help you discover amazing products, check out what other shoppers are saying, and find that perfect item you didn't even know you needed! 

Want to place orders or track purchases? Just create an account - it takes like 30 seconds, I promise I counted! ⏱️

So, what brings you to our little corner of the internet today? Looking for something specific or just window shopping? Either way, I'm here to help! 😊"
"""
        
        prompt = f"""
You are a fun, enthusiastic SALES ASSISTANT at an e-commerce store. Think of yourself as a friendly shop owner who LOVES their products and genuinely wants to help customers find what they need.

YOUR PERSONALITY:
🎭 Humorous - Use light jokes, playful language, and fun emojis
🌟 Enthusiastic - Get excited about products and helping customers
🤝 Proactive - Always ask follow-up questions and offer suggestions
💬 Conversational - Chat like a friendly salesperson, not a robot
🎯 Helpful - Your goal is to help visitors find and love products

WHAT YOU CAN ACCESS:
✅ Products (names, descriptions, prices, stock, colors, sizes, materials, product_url)
✅ Product reviews and ratings
✅ Product categories  
✅ Featured and popular products

WHAT YOU CANNOT ACCESS:
❌ Order information (they need to sign up first - encourage this!)
❌ User accounts, payments, shipping details

{intro_message}

HOW TO RESPOND:
1. **Be a Seller** - You're selling products you believe in! Show enthusiasm
2. **Include Product Links** - When mentioning products, include the product URL or link
3. **Ask Follow-up Questions** - End responses with engaging questions like:
   - "Does this catch your eye? 👀"
   - "Would you like me to find more options like this?"
   - "Is this the style you're going for, or should we explore other directions?"
   - "Need any other details before you fall in love with it? 😄"
   - "What do you think? Should I show you similar items?"
   - "Anything else I can help you find today?"
4. **Be Proactive** - Suggest related products, mention deals, offer alternatives
5. **Use Humor** - Light jokes, fun comparisons, playful language
6. **Create Urgency (gently)** - Mention low stock, popular items, limited time

FORMATTING:
- 🏷️ Show prices clearly: "$29.99" or "~~$39.99~~ **$29.99** (You save $10!)"
- 🔗 Include product links when available
- ⭐ Show ratings: "⭐ 4.8/5 (from 120 happy customers!)"
- 📦 Stock status: "Only 3 left - they're flying off the shelves!"
- Use emojis to make it fun and scannable
- Keep it conversational, not like a boring product catalog

EXAMPLE TONE:
"Ooh, great choice! 🎉 This jacket is basically a hug you can wear - super cozy AND stylish. It's got a 4.9 star rating because, well, it's awesome! 
👉 Check it out here: [product link]
Only 5 left in stock though - winter's coming and people are snatching these up! ❄️
Want me to show you what others pair it with, or are you ready to make it yours?"

Context from database:
{context}

Visitor's Question: {query}

Respond as an enthusiastic, helpful sales assistant. Be fun, include product links when available, and always end with an engaging follow-up question:
"""
        
        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return context if context else "I'm sorry, I couldn't process your request. Please try again."
    
    def process_query(self, query: str, return_debug: bool = False) -> Any:
        """Process visitor query - products and reviews only
        
        Args:
            query: Visitor's question
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
            'query_type': 'visitor_query',
            'is_intro': is_intro_query,
            'data_accessed': []
        }
        
        try:
            conn = self.get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                
                # Handle account-required requests
                account_keywords = ['my order', 'my orders', 'order status', 'track order', 
                                   'my account', 'my profile', 'my cart', 'checkout',
                                   'my purchase', 'order history', 'my payment']
                if any(word in query_lower for word in account_keywords):
                    context_parts.append(
                        "ACCOUNT_REQUIRED: The visitor is asking about account-related features. "
                        "Politely inform them they need to sign up or log in to access orders, cart, and account features."
                    )
                    debug_info['data_accessed'].append('account_required_notice')
                
                # Check for product queries
                if any(word in query_lower for word in ['product', 'item', 'buy', 'price', 'stock', 
                                                         'available', 'cost', 'how much', 'find', 'search', 'looking for']):
                    cur.execute("""
                        SELECT product_id, name, description, price, sale_price, stock, category_name, product_url
                        FROM products 
                        WHERE is_active = true
                        ORDER BY featured DESC, created_at DESC 
                        LIMIT 10
                    """)
                    products = cur.fetchall()
                    context_parts.append(f"Available Products: {products}")
                    debug_info['data_accessed'].append('products')
                    
                    cur.execute("SELECT COUNT(*) as total FROM products WHERE is_active = true")
                    count = cur.fetchone()
                    context_parts.append(f"Total Products Available: {count['total']}")
                
                # Check for review queries
                if any(word in query_lower for word in ['review', 'rating', 'feedback', 'opinion', 
                                                         'rated', 'stars', 'recommend']):
                    cur.execute("""
                        SELECT pr.rating, pr.review_text, pr.created_at, p.name as product_name
                        FROM product_review pr
                        JOIN products p ON pr.product_id::text = p.product_id::text
                        ORDER BY pr.created_at DESC 
                        LIMIT 10
                    """)
                    reviews = cur.fetchall()
                    context_parts.append(f"Recent Product Reviews: {reviews}")
                    debug_info['data_accessed'].append('reviews')
                    
                    # Also get top rated products
                    top_rated = self.get_top_rated_products(5)
                    if top_rated:
                        context_parts.append(f"Top Rated Products: {top_rated}")
                
                # Check for category queries
                if any(word in query_lower for word in ['category', 'categories', 'type', 'kinds', 'section']):
                    categories = self.get_categories()
                    context_parts.append(f"Product Categories: {categories}")
                    debug_info['data_accessed'].append('categories')
                
                # Check for featured/popular products
                if any(word in query_lower for word in ['featured', 'popular', 'best', 'top', 
                                                         'recommend', 'suggestion', 'trending', 'hot']):
                    featured = self.get_featured_products()
                    context_parts.append(f"Featured Products: {featured}")
                    debug_info['data_accessed'].append('featured_products')
                    
                    top_rated = self.get_top_rated_products(5)
                    if top_rated:
                        context_parts.append(f"Top Rated Products: {top_rated}")
                
                # Check for sale/discount queries
                if any(word in query_lower for word in ['sale', 'discount', 'deal', 'offer', 'cheap', 'affordable']):
                    cur.execute("""
                        SELECT product_id, name, price, sale_price, category_name
                        FROM products
                        WHERE sale_price IS NOT NULL AND sale_price < price AND is_active = true
                        ORDER BY (price - sale_price) DESC
                        LIMIT 10
                    """)
                    sale_products = cur.fetchall()
                    if sale_products:
                        context_parts.append(f"Products on Sale: {sale_products}")
                    else:
                        context_parts.append("No products currently on sale.")
                    debug_info['data_accessed'].append('sale_products')
                
                # If no specific context matched, provide general product info
                if not context_parts and not is_intro_query:
                    cur.execute("SELECT COUNT(*) as total_products FROM products WHERE is_active = true")
                    stats = cur.fetchone()
                    context_parts.append(f"We have {stats['total_products']} products available for you to explore.")
                    
                    featured = self.get_featured_products(5)
                    if featured:
                        context_parts.append(f"Featured Products: {featured}")
                    
                    categories = self.get_categories()
                    if categories:
                        context_parts.append(f"Browse by Category: {categories}")
                    
                    debug_info['data_accessed'].append('general_browse')
            
            conn.close()
        except Exception as e:
            logger.error(f"Error fetching database context: {e}")
            context_parts.append("I encountered an issue retrieving product information. Please try again.")
            debug_info['error'] = str(e)
        
        # Combine all context
        context = "\n\n".join(context_parts) if context_parts else "No specific data retrieved."
        
        # Generate response with LLM
        response = self.generate_llm_response(query, context, is_intro_query=is_intro_query)
        
        if return_debug:
            return response, debug_info
        return response
