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
    
    def get_user_orders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get orders for the current user only"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT o.order_id, o.status, o.order_total, o.currency, 
                           o.created_at, o.subtotal, o.tax, o.shipping_charges, o.discount
                    FROM orders o
                    WHERE o.user_id = %s
                    ORDER BY o.created_at DESC
                    LIMIT 20
                """, (user_id,))
                return cur.fetchall()
        finally:
            conn.close()
    
    def get_user_order_details(self, user_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Get specific order with items for user - ensures user can only see their own orders"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get order details
                cur.execute("""
                    SELECT o.order_id, o.status, o.order_total, o.currency, 
                           o.created_at, o.subtotal, o.tax, o.shipping_charges, 
                           o.discount, o.shipping_info
                    FROM orders o
                    WHERE o.order_id = %s AND o.user_id = %s
                """, (order_id, user_id))
                order = cur.fetchone()
                
                if order:
                    # Get order items
                    cur.execute("""
                        SELECT oi.quantity, oi.unit_price, oi.total_price, p.name as product_name
                        FROM order_items oi
                        LEFT JOIN products p ON oi.product_id = p.product_id
                        WHERE oi.order_id = %s
                    """, (order_id,))
                    items = cur.fetchall()
                    order['items'] = items
                
                return order
        finally:
            conn.close()
    
    def get_user_order_shipment(self, user_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Get shipment info for user's order"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT s.tracking_number, s.carrier, s.status, s.shipped_at, s.delivered_at
                    FROM shipments s
                    JOIN orders o ON s.order_id = o.order_id
                    WHERE o.order_id = %s AND o.user_id = %s
                """, (order_id, user_id))
                return cur.fetchone()
        finally:
            conn.close()
    
    def search_products(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search products by name or description"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT product_id, name, description, price, sale_price, 
                           stock, category_name, colors, sizes, materials, product_url
                    FROM products
                    WHERE (name ILIKE %s OR description ILIKE %s) AND is_active = true
                    ORDER BY featured DESC, created_at DESC
                    LIMIT %s
                """, (f'%{search_term}%', f'%{search_term}%', limit))
                return cur.fetchall()
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

Provide a helpful, personalized response:
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
            conn = self.get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                
                # Check for user's own order queries
                if user_id and any(word in query_lower for word in ['my order', 'my orders', 'order status', 
                                                                      'track order', 'my purchase', 'order history',
                                                                      'where is my', 'delivery', 'shipping']):
                    orders = self.get_user_orders(user_id)
                    if orders:
                        context_parts.append(f"Your Orders: {orders}")
                        debug_info['data_accessed'].append('user_orders')
                        
                        # Get shipment info for recent orders
                        for order in orders[:3]:  # Check first 3 orders for shipment
                            shipment = self.get_user_order_shipment(user_id, str(order['order_id']))
                            if shipment:
                                context_parts.append(f"Shipment for Order {order['order_id']}: {shipment}")
                    else:
                        context_parts.append("You don't have any orders yet. Start shopping to place your first order!")
                
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
                
                # Check for product queries
                if any(word in query_lower for word in ['product', 'item', 'buy', 'price', 'stock', 
                                                         'available', 'find', 'search', 'looking for']):
                    cur.execute("""
                        SELECT product_id, name, description, price, sale_price, stock, category_name, product_url
                        FROM products 
                        WHERE is_active = true
                        ORDER BY featured DESC, created_at DESC 
                        LIMIT 10
                    """)
                    products = cur.fetchall()
                    context_parts.append(f"Products: {products}")
                    debug_info['data_accessed'].append('products')
                
                # Check for review queries
                if any(word in query_lower for word in ['review', 'rating', 'feedback', 'opinion']):
                    cur.execute("""
                        SELECT pr.rating, pr.review_text, pr.created_at, p.name as product_name
                        FROM product_review pr
                        JOIN products p ON pr.product_id::text = p.product_id::text
                        ORDER BY pr.created_at DESC 
                        LIMIT 10
                    """)
                    reviews = cur.fetchall()
                    context_parts.append(f"Recent Reviews: {reviews}")
                    debug_info['data_accessed'].append('reviews')
                
                # Check for category queries
                if any(word in query_lower for word in ['category', 'categories', 'type', 'kinds']):
                    categories = self.get_categories()
                    context_parts.append(f"Categories: {categories}")
                    debug_info['data_accessed'].append('categories')
                
                # Check for featured/popular products
                if any(word in query_lower for word in ['featured', 'popular', 'best', 'recommend', 'suggestion']):
                    featured = self.get_featured_products()
                    context_parts.append(f"Featured Products: {featured}")
                    debug_info['data_accessed'].append('featured_products')
                
                # If no specific context matched, provide helpful info
                if not context_parts and not is_intro_query:
                    if user_id:
                        # Show user's recent orders and featured products
                        orders = self.get_user_orders(user_id)
                        if orders:
                            context_parts.append(f"Your Recent Orders: {orders[:5]}")
                        
                    featured = self.get_featured_products(5)
                    if featured:
                        context_parts.append(f"Featured Products: {featured}")
                    
                    cur.execute("SELECT COUNT(*) as total_products FROM products WHERE is_active = true")
                    stats = cur.fetchone()
                    context_parts.append(f"We have {stats['total_products']} products available.")
                    debug_info['data_accessed'].append('general_stats')
            
            conn.close()
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