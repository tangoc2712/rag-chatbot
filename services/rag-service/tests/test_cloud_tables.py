#!/usr/bin/env python3
"""
Test script for the enhanced RAG chatbot with multi-table support
Tests semantic search and SQL generation across all cloud tables
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_chat(message: str, session_id: str = "test-session") -> Dict[str, Any]:
    """Send a message to the chatbot"""
    response = requests.post(
        f"{BASE_URL}/chat/message",
        json={
            "message": message,
            "session_id": session_id
        }
    )
    return response.json()

def print_response(query: str, response: Dict[str, Any]):
    """Pretty print the chatbot response"""
    print(f"\n{'='*80}")
    print(f"USER: {query}")
    print(f"{'='*80}")
    print(f"BOT: {response.get('response', 'No response')}")
    print(f"{'='*80}\n")

def main():
    """Run comprehensive tests"""
    
    print("🤖 Testing Enhanced E-commerce RAG Chatbot")
    print("Testing multi-table semantic search and SQL generation\n")
    
    # Test 1: Product search (products table)
    print("Test 1: Product Search")
    resp = test_chat("Show me laptops")
    print_response("Show me laptops", resp)
    
    # Test 2: User search (users table)
    print("\nTest 2: User Search")
    resp = test_chat("Find customers who work as engineers")
    print_response("Find customers who work as engineers", resp)
    
    # Test 3: Order search (orders table)
    print("\nTest 3: Order Search")
    resp = test_chat("Show me recent orders")
    print_response("Show me recent orders", resp)
    
    # Test 4: Review search (product_reviews table)
    print("\nTest 4: Product Reviews")
    resp = test_chat("Show me 5-star reviews")
    print_response("Show me 5-star reviews", resp)
    
    # Test 5: Inventory search (inventory table)
    print("\nTest 5: Inventory Check")
    resp = test_chat("Which products have low stock?")
    print_response("Which products have low stock?", resp)
    
    # Test 6: Coupon search (coupons table)
    print("\nTest 6: Active Coupons")
    resp = test_chat("What discounts are available?")
    print_response("What discounts are available?", resp)
    
    # Test 7: Shipment tracking (shipments table)
    print("\nTest 7: Shipment Tracking")
    resp = test_chat("Show me pending shipments")
    print_response("Show me pending shipments", resp)
    
    # Test 8: Payment status (payments table)
    print("\nTest 8: Payment Status")
    resp = test_chat("Show me completed payments")
    print_response("Show me completed payments", resp)
    
    # Test 9: Category search (categories table)
    print("\nTest 9: Category Search")
    resp = test_chat("List all product categories")
    print_response("List all product categories", resp)
    
    # Test 10: Complex multi-table query
    print("\nTest 10: Complex Multi-table Query")
    resp = test_chat("Show me users who have pending orders with their payment status")
    print_response("Show me users who have pending orders with their payment status", resp)
    
    # Test 11: Semantic search across tables
    print("\nTest 11: Multi-table Semantic Search")
    resp = test_chat("electronics")
    print_response("electronics", resp)
    
    # Test 12: Order details with items
    print("\nTest 12: Order Details")
    resp = test_chat("Show order details with items for order 1")
    print_response("Show order details with items for order 1", resp)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
