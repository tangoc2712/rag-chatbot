"""
Cleanup all dummy data from cloud PostgreSQL database.
"""
import psycopg2

# Database connection details
DB_CONFIG = {
    'host': '34.177.103.63',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'Huypn456785@1'
}

print("Connecting to Cloud PostgreSQL...")
conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = False
cursor = conn.cursor()

try:
    print("\n=== CLEANING UP DUMMY DATA ===\n")
    
    # Delete in reverse order of foreign key dependencies
    
    print("Deleting dummy events...")
    cursor.execute("DELETE FROM events WHERE session_id LIKE 'DUMMY%'")
    print(f"✓ Deleted {cursor.rowcount} events")
    
    print("Deleting dummy cart_items...")
    cursor.execute("""
        DELETE FROM cart_items 
        WHERE cart_id IN (
            SELECT id FROM carts 
            WHERE user_id IN (SELECT user_id FROM users WHERE email LIKE 'DUMMY%')
        )
    """)
    print(f"✓ Deleted {cursor.rowcount} cart items")
    
    print("Deleting dummy carts...")
    cursor.execute("DELETE FROM carts WHERE user_id IN (SELECT user_id FROM users WHERE email LIKE 'DUMMY%')")
    print(f"✓ Deleted {cursor.rowcount} carts")
    
    print("Deleting dummy shipments...")
    cursor.execute("DELETE FROM shipments WHERE tracking_number LIKE 'DUMMY%'")
    print(f"✓ Deleted {cursor.rowcount} shipments")
    
    print("Deleting dummy product_reviews...")
    cursor.execute("DELETE FROM product_reviews WHERE comment LIKE 'DUMMY%'")
    print(f"✓ Deleted {cursor.rowcount} reviews")
    
    print("Deleting dummy payments...")
    cursor.execute("DELETE FROM payments WHERE order_id IN (SELECT order_id FROM orders WHERE user_id LIKE 'DUMMY%')")
    print(f"✓ Deleted {cursor.rowcount} payments")
    
    print("Deleting dummy order_items...")
    cursor.execute("DELETE FROM order_items WHERE order_id IN (SELECT order_id FROM orders WHERE user_id LIKE 'DUMMY%')")
    print(f"✓ Deleted {cursor.rowcount} order items")
    
    print("Deleting dummy orders...")
    cursor.execute("DELETE FROM orders WHERE user_id LIKE 'DUMMY%'")
    print(f"✓ Deleted {cursor.rowcount} orders")
    
    print("Deleting dummy inventory...")
    cursor.execute("DELETE FROM inventory WHERE product_id IN (SELECT product_id FROM products WHERE sku LIKE 'DUMMY%')")
    print(f"✓ Deleted {cursor.rowcount} inventory entries")
    
    print("Deleting dummy coupons...")
    cursor.execute("DELETE FROM coupons WHERE code LIKE 'DUMMY%'")
    print(f"✓ Deleted {cursor.rowcount} coupons")
    
    print("Deleting dummy products...")
    cursor.execute("DELETE FROM products WHERE sku LIKE 'DUMMY%'")
    print(f"✓ Deleted {cursor.rowcount} products")
    
    print("Deleting dummy categories...")
    cursor.execute("DELETE FROM categories WHERE name LIKE 'DUMMY%'")
    print(f"✓ Deleted {cursor.rowcount} categories")
    
    print("Deleting dummy users...")
    cursor.execute("DELETE FROM users WHERE email LIKE 'DUMMY%'")
    print(f"✓ Deleted {cursor.rowcount} users")
    
    # Commit
    conn.commit()
    print("\n✅ CLEANUP COMPLETE!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    conn.rollback()
    raise
finally:
    cursor.close()
    conn.close()
