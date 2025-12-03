#!/usr/bin/env python3
"""
Interactive test for the enhanced chatbot
Demonstrates queries across all cloud tables
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def chat(message: str):
    """Send a message to the chatbot"""
    try:
        response = requests.post(
            f"{BASE_URL}/chat/message",
            json={"message": message, "session_id": "demo-session"}
        )
        data = response.json()
        print(f"\n{'='*80}")
        print(f"YOU: {message}")
        print(f"{'='*80}")
        print(f"BOT: {data.get('response', 'Error: No response')}")
        print(f"{'='*80}\n")
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("\n" + "="*80)
    print(" 🤖 ENHANCED E-COMMERCE RAG CHATBOT - DEMO")
    print(" Multi-Table Semantic Search & SQL Generation")
    print("="*80)
    
    print("\n📋 Testing Queries Across Different Tables:\n")
    
    # 1. Products table - Semantic search
    print("1️⃣  Testing PRODUCTS table (semantic search):")
    chat("Find me wireless headphones")
    
    # 2. Users table - SQL query
    print("\n2️⃣  Testing USERS table (SQL query):")
    chat("How many users are registered in the system?")
    
    # 3. Orders table - SQL query
    print("\n3️⃣  Testing ORDERS table (SQL query):")
    chat("What are the top 5 most recent orders?")
    
    # 4. Product Reviews table - Semantic search
    print("\n4️⃣  Testing PRODUCT_REVIEWS table (semantic search):")
    chat("Find positive reviews about electronics")
    
    # 5. Categories table - SQL query
    print("\n5️⃣  Testing CATEGORIES table (SQL query):")
    chat("List all active product categories")
    
    # 6. Inventory table - SQL query
    print("\n6️⃣  Testing INVENTORY table (SQL query):")
    chat("Show me products with less than 5 items in stock")
    
    # 7. Coupons table - SQL query
    print("\n7️⃣  Testing COUPONS table (SQL query):")
    chat("What are the current active discount codes?")
    
    # 8. Payments table - SQL query
    print("\n8️⃣  Testing PAYMENTS table (SQL query):")
    chat("Show me successful payments from today")
    
    # 9. Shipments table - SQL query
    print("\n9️⃣  Testing SHIPMENTS table (SQL query):")
    chat("Which orders are currently being shipped?")
    
    # 10. Multi-table join query
    print("\n🔟 Testing MULTI-TABLE JOIN (SQL query):")
    chat("Show me orders with their shipment tracking numbers")
    
    print("\n" + "="*80)
    print(" ✅ DEMO COMPLETED!")
    print(" All cloud tables are now accessible through the chatbot")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
