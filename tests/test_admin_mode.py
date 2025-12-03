"""
Test Admin Mode - Full Database Access
Tests the chatbot with admin-level access to all tables
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag.admin_assistant import ECommerceRAG
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_admin_queries():
    """Test various admin-level queries across all tables"""
    
    rag = ECommerceRAG()
    
    test_queries = [
        # General greeting
        "Hello, who are you?",
        
        # Products queries
        "Show me the top 5 products by price",
        "Find products in the electronics category",
        "What are the highest rated products?",
        
        # Users queries
        "How many users are registered?",
        "List users with admin role",
        "Show me recent user registrations",
        
        # Orders queries
        "What are the pending orders?",
        "Show me the latest 5 orders",
        "How many orders were placed this month?",
        "What's the total revenue from completed orders?",
        
        # Reviews queries
        "Show me the latest product reviews",
        "Find products with 5-star reviews",
        "What are the most reviewed products?",
        
        # Inventory queries
        "What products are low in stock?",
        "Show inventory for all products",
        
        # Payments queries
        "List recent successful payments",
        "What's the total payment amount today?",
        
        # Shipments queries
        "Show pending shipments",
        "What orders have been delivered?",
        
        # Coupons queries
        "List all active coupons",
        "Show coupons with highest discount",
        
        # Shopping cart queries
        "Show active shopping carts",
        "What items are in carts but not purchased?",
        
        # Multi-table complex queries
        "Show me orders with their payment status",
        "List products with their average ratings",
        "Find users who made orders this week",
    ]
    
    print("=" * 80)
    print("TESTING ADMIN MODE - FULL DATABASE ACCESS")
    print("=" * 80)
    print()
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        print(f"{'='*80}")
        
        try:
            # Process without customer_id (admin mode)
            response = rag.process_query(query)
            print(f"\nResponse:\n{response}")
            print()
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            logger.error(f"Error processing query '{query}': {e}")
        
        print("-" * 80)
    
    print("\n" + "="*80)
    print("ADMIN MODE TESTING COMPLETED")
    print("="*80)

if __name__ == "__main__":
    test_admin_queries()
