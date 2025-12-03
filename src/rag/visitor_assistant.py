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
    
    def semantic_search(self, query: str, tables: List[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search across specified tables using pgvector
        For visitors: only products and product_reviews
        """
        if not self.settings.GOOGLE_API_KEY:
            logger.warning("Cannot perform semantic search without GOOGLE_API_KEY")
            return []

        # Visitors can only access products and reviews
        allowed_tables = ['products', 'product_review', 'category']
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
                        elif table == 'category':
                            sql = """
                                SELECT 'category' as _source_table,
                                       category_id, name, type,
                                       embedding <=> %s::vector as distance
                                FROM category
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
            
            # Determine which tables to search based on query
            tables_to_search = []
            
            if any(word in query_lower for word in ['review', 'rating', 'feedback', 'opinion', 
                                                     'rated', 'stars', 'recommend']):
                tables_to_search.append('product_review')
                debug_info['data_accessed'].append('reviews')
            
            if any(word in query_lower for word in ['category', 'categories', 'type', 'kinds', 'section']):
                tables_to_search.append('category')
                debug_info['data_accessed'].append('categories')
            
            # Default to products for most queries
            if any(word in query_lower for word in ['product', 'item', 'buy', 'price', 'stock', 
                                                     'available', 'cost', 'how much', 'find', 'search', 
                                                     'looking for', 'featured', 'popular', 'best', 'top',
                                                     'recommend', 'suggestion', 'trending', 'hot',
                                                     'sale', 'discount', 'deal', 'offer', 'cheap', 'affordable']):
                tables_to_search.append('products')
                debug_info['data_accessed'].append('products')
            
            # If no specific table matched, search products by default (unless intro query)
            if not tables_to_search and not is_intro_query:
                tables_to_search = ['products', 'product_review']
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
                        cur.execute("SELECT COUNT(*) as total_products FROM products WHERE is_active = true")
                        stats = cur.fetchone()
                        context_parts.append(f"We have {stats['total_products']} products available for you to explore.")
                finally:
                    conn.close()
                debug_info['data_accessed'].append('general_stats')
        
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
