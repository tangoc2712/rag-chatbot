#!/usr/bin/env python3
"""
Test script for new REST API endpoints
Tests all the newly created endpoints for cloud tables
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint: str, description: str):
    """Test an API endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"Endpoint: {endpoint}")
    print(f"{'='*80}")
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Status: {response.status_code}")
            print(f"Response preview: {json.dumps(data, indent=2, default=str)[:500]}...")
        else:
            print(f"❌ Error! Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def main():
    """Run API endpoint tests"""
    
    print("🧪 Testing New Cloud Table API Endpoints")
    
    # Test Users endpoints
    test_endpoint("/users?limit=5", "Get Users (limit 5)")
    test_endpoint("/users?is_active=true&limit=3", "Get Active Users")
    
    # Test Categories endpoints
    test_endpoint("/categories", "Get All Categories")
    test_endpoint("/categories?is_active=true", "Get Active Categories")
    
    # Test Reviews endpoints
    test_endpoint("/reviews?limit=5", "Get Product Reviews")
    test_endpoint("/reviews?min_rating=5&limit=5", "Get 5-Star Reviews")
    
    # Test Inventory endpoints
    test_endpoint("/inventory?limit=10", "Get Inventory")
    test_endpoint("/inventory?low_stock=true&limit=5", "Get Low Stock Items")
    
    # Test Coupons endpoints
    test_endpoint("/coupons?active_only=true", "Get Active Coupons")
    
    # Test Shipments endpoints
    test_endpoint("/shipments?limit=5", "Get Recent Shipments")
    
    # Test Payments endpoints
    test_endpoint("/payments?limit=5", "Get Recent Payments")
    
    # Test Products (existing)
    test_endpoint("/products?limit=3", "Get Products")
    
    # Test Orders (existing)
    test_endpoint("/orders?limit=3", "Get Orders")
    
    # Test Health Check
    test_endpoint("/health", "Health Check")
    
    print("\n" + "="*80)
    print("✅ API endpoint tests completed!")
    print("="*80)

if __name__ == "__main__":
    main()
