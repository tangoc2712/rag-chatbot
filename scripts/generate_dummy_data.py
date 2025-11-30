"""
Generate 10,000 dummy orders with all related data for testing embedding DAGs.
All dummy data is identifiable by 'DUMMY_' prefix in key fields for easy deletion.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
import uuid
import psycopg2
from psycopg2.extras import execute_batch

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
    print("\n=== GENERATING DUMMY DATA ===\n")
    
    # 1. Get existing role IDs
    cursor.execute("SELECT role_id FROM roles LIMIT 1")
    default_role_id = cursor.fetchone()[0]
    
    # 2. Create 1,000 dummy users
    print("Creating 1,000 dummy users...")
    users_data = []
    user_ids = []
    for i in range(1, 1001):
        user_id = str(uuid.uuid4())
        user_ids.append(user_id)
        users_data.append((
            user_id,
            f'DUMMY_user{i}@test.com',
            'dummy_hash',
            f'DUMMY User {i}',
            f'+1-555-{str(i).zfill(7)}',
            f'DUMMY {i} Main St',
            datetime.now() - timedelta(days=random.randint(0, 365)),
            datetime.now(),
            True,
            None,
            default_role_id,
            datetime.now().date() - timedelta(days=random.randint(7300, 25550)),
            'DUMMY Job',
            random.choice([True, False])
        ))
    
    execute_batch(cursor, """
        INSERT INTO users (user_id, email, password_hash, full_name, phone, address, 
                          created_at, updated_at, is_active, img_url, role_id, date_of_birth, job, gender)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, users_data)
    print(f"✓ Created {len(users_data)} users")
    
    # 3. Create 10 dummy categories
    print("Creating 10 dummy categories...")
    categories_data = [
        ('DUMMY Electronics', None, 'product_category'),
        ('DUMMY Clothing', None, 'product_category'),
        ('DUMMY Books', None, 'product_category'),
        ('DUMMY Home', None, 'product_category'),
        ('DUMMY Sports', None, 'product_category'),
        ('DUMMY Toys', None, 'product_category'),
        ('DUMMY Food', None, 'product_category'),
        ('DUMMY Beauty', None, 'product_category'),
        ('DUMMY Automotive', None, 'product_category'),
        ('DUMMY Garden', None, 'product_category')
    ]
    execute_batch(cursor, """
        INSERT INTO categories (name, parent_category_id, type)
        VALUES (%s, %s, %s)
    """, categories_data)
    
    cursor.execute("SELECT category_id FROM categories WHERE name LIKE 'DUMMY%'")
    dummy_category_ids = [row[0] for row in cursor.fetchall()]
    print(f"✓ Created {len(dummy_category_ids)} categories")
    
    # 4. Create 2,000 dummy products
    print("Creating 2,000 dummy products...")
    products_data = []
    product_ids = []
    for i in range(1, 2001):
        product_id = str(uuid.uuid4())
        product_ids.append(product_id)
        products_data.append((
            product_id,
            f'DUMMY-SKU-{str(i).zfill(6)}',
            f'DUMMY Product {i}',
            f'DUMMY This is test product {i} for demonstration purposes. High quality and affordable.',
            round(random.uniform(10, 1000), 2),
            'USD',
            random.choice(dummy_category_ids),
            True,
            None,
            f'https://dummy.example.com/product/{i}',
            datetime.now() - timedelta(days=random.randint(0, 180)),
            datetime.now()
        ))
    
    execute_batch(cursor, """
        INSERT INTO products (product_id, sku, name, description, price, currency, 
                             category_id, is_active, sale_price, product_url, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, products_data)
    print(f"✓ Created {len(products_data)} products")
    
    # 5. Create 10,000 dummy orders
    print("Creating 10,000 dummy orders...")
    orders_data = []
    order_ids = []
    for i in range(1, 10001):
        order_id = str(uuid.uuid4())
        order_ids.append(order_id)
        orders_data.append((
            order_id,
            f'DUMMY_user{random.randint(1, 1000)}@test.com',  # user_id is text (email)
            random.choice(['pending', 'processing', 'shipped', 'delivered', 'cancelled']),
            round(random.uniform(20, 500), 2),
            'USD',
            datetime.now() - timedelta(days=random.randint(0, 90)),
            datetime.now()
        ))
    
    execute_batch(cursor, """
        INSERT INTO orders (order_id, user_id, status, order_total, currency, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, orders_data, page_size=500)
    print(f"✓ Created {len(orders_data)} orders")
    
    # 6. Create order items (avg 2.5 items per order = 25,000 items)
    print("Creating ~25,000 order items...")
    order_items_data = []
    for order_id in order_ids:
        num_items = random.randint(1, 5)
        for _ in range(num_items):
            product_id = random.choice(product_ids)
            quantity = random.randint(1, 5)
            unit_price = round(random.uniform(10, 200), 2)
            order_items_data.append((
                str(uuid.uuid4()),
                order_id,
                product_id,
                quantity,
                unit_price,
                unit_price * quantity
            ))
    
    execute_batch(cursor, """
        INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, total_price)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, order_items_data, page_size=1000)
    print(f"✓ Created {len(order_items_data)} order items")
    
    # 7. Create payments (1 per order)
    print("Creating 10,000 payments...")
    payments_data = []
    for order_id in order_ids:
        payments_data.append((
            str(uuid.uuid4()),
            order_id,
            round(random.uniform(20, 500), 2),
            random.choice(['credit_card', 'debit_card', 'paypal', 'bank_transfer']),
            random.choice(['pending', 'completed', 'failed', 'refunded']),
            datetime.now() - timedelta(days=random.randint(0, 90))
        ))
    
    execute_batch(cursor, """
        INSERT INTO payments (payment_id, order_id, amount, method, status, paid_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, payments_data, page_size=1000)
    print(f"✓ Created {len(payments_data)} payments")
    
    # 8. Create shipments (80% of orders)
    print("Creating ~8,000 shipments...")
    shipments_data = []
    # Get a carrier (user)
    cursor.execute("SELECT user_id FROM users WHERE email LIKE 'DUMMY%' LIMIT 1")
    carrier_id = cursor.fetchone()[0]
    
    for order_id in random.sample(order_ids, int(len(order_ids) * 0.8)):
        shipped_at = datetime.now() - timedelta(days=random.randint(0, 30))
        delivered_at = shipped_at + timedelta(days=random.randint(1, 15)) if random.random() > 0.3 else None
        shipments_data.append((
            str(uuid.uuid4()),
            order_id,
            f'DUMMY-TRACK-{uuid.uuid4().hex[:12].upper()}',
            random.choice(['in_transit', 'delivered', 'returned']),
            shipped_at,
            delivered_at,
            carrier_id
        ))
    
    execute_batch(cursor, """
        INSERT INTO shipments (shipment_id, order_id, tracking_number, status, shipped_at, delivered_at, carrier_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, shipments_data, page_size=1000)
    print(f"✓ Created {len(shipments_data)} shipments")
    
    # 9. Create product reviews (5,000 reviews)
    print("Creating 5,000 product reviews...")
    reviews_data = []
    review_templates = [
        'DUMMY Review: Great product, highly recommended!',
        'DUMMY Review: Good value for money.',
        'DUMMY Review: Satisfied with the purchase.',
        'DUMMY Review: Could be better, but acceptable.',
        'DUMMY Review: Not what I expected.',
        'DUMMY Review: Excellent quality!',
        'DUMMY Review: Fast shipping and good packaging.',
        'DUMMY Review: Average product, nothing special.'
    ]
    
    for _ in range(5000):
        reviews_data.append((
            str(uuid.uuid4()),
            random.choice(product_ids),
            random.choice(user_ids),
            random.randint(1, 5),
            random.choice(review_templates),
            datetime.now() - timedelta(days=random.randint(0, 60))
        ))
    
    execute_batch(cursor, """
        INSERT INTO product_reviews (review_id, product_id, user_id, rating, comment, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, reviews_data, page_size=1000)
    print(f"✓ Created {len(reviews_data)} reviews")
    
    # 10. Create carts (500 carts)
    print("Creating 500 carts...")
    carts_data = []
    cart_ids = []
    for user_id in random.sample(user_ids, 500):
        cart_id = random.randint(1000000, 9999999)  # cart id is integer
        cart_ids.append(cart_id)
        carts_data.append((
            cart_id,
            user_id,
            random.choice(['active', 'abandoned', 'ordered']),
            round(random.uniform(10, 300), 2),
            datetime.now() - timedelta(days=random.randint(0, 7)),
            datetime.now()
        ))
    
    execute_batch(cursor, """
        INSERT INTO carts (id, user_id, status, total_price, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, carts_data)
    print(f"✓ Created {len(carts_data)} carts")
    
    # 11. Create cart items (~1,500 items)
    print("Creating ~1,500 cart items...")
    cart_items_data = []
    for cart_id in cart_ids:
        num_items = random.randint(1, 5)
        for _ in range(num_items):
            product_id = random.choice(product_ids)
            quantity = random.randint(1, 3)
            unit_price = round(random.uniform(10, 200), 2)
            cart_items_data.append((
                cart_id,
                product_id,
                quantity,
                unit_price
            ))
    
    execute_batch(cursor, """
        INSERT INTO cart_items (cart_id, product_id, quantity, unit_price)
        VALUES (%s, %s, %s, %s)
    """, cart_items_data)
    print(f"✓ Created {len(cart_items_data)} cart items")
    
    # 12. Create inventory (2,000 entries - 1 per product)
    print("Creating 2,000 inventory entries...")
    inventory_data = []
    for product_id in product_ids:
        inventory_data.append((
            str(uuid.uuid4()),
            product_id,
            None,  # warehouse_id
            random.randint(50, 1000),
            datetime.now()
        ))
    
    execute_batch(cursor, """
        INSERT INTO inventory (inventory_id, product_id, warehouse_id, quantity, last_updated)
        VALUES (%s, %s, %s, %s, %s)
    """, inventory_data, page_size=1000)
    print(f"✓ Created {len(inventory_data)} inventory entries")
    
    # 13. Create coupons (100 coupons)
    print("Creating 100 coupons...")
    coupons_data = []
    for i in range(100):
        coupons_data.append((
            str(uuid.uuid4()),
            f'DUMMY-{uuid.uuid4().hex[:8].upper()}',
            random.choice(['percent', 'amount']),
            round(random.uniform(5, 50), 2),
            datetime.now() - timedelta(days=30),
            datetime.now() + timedelta(days=60),
            random.randint(0, 50),
            datetime.now(),
            datetime.now()
        ))
    
    execute_batch(cursor, """
        INSERT INTO coupons (coupon_id, code, discount_type, value, valid_from, valid_to, usage_count, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, coupons_data)
    print(f"✓ Created {len(coupons_data)} coupons")
    
    # 14. Create events (20,000 events)
    print("Creating 20,000 events...")
    events_data = []
    event_types = ['page_view', 'add_to_cart', 'checkout', 'purchase', 'search', 'login', 'logout']
    for i in range(20000):
        events_data.append((
            str(uuid.uuid4()),
            random.choice(user_ids),
            f'DUMMY-SESSION-{uuid.uuid4()}',
            random.choice(event_types),
            f'{{"dummy": true, "event_num": {i}}}',
            datetime.now() - timedelta(days=random.randint(0, 30))
        ))
    
    execute_batch(cursor, """
        INSERT INTO events (event_id, user_id, session_id, event_type, metadata, ts)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, events_data, page_size=1000)
    print(f"✓ Created {len(events_data)} events")
    
    # Commit all changes
    conn.commit()
    
    print("\n=== VERIFICATION ===\n")
    
    # Verify counts
    tables_to_check = [
        ("users WHERE email LIKE 'DUMMY%'", "Users"),
        ("categories WHERE name LIKE 'DUMMY%'", "Categories"),
        ("products WHERE sku LIKE 'DUMMY%'", "Products"),
        ("orders WHERE user_id LIKE 'DUMMY%'", "Orders"),
        ("order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.user_id LIKE 'DUMMY%'", "Order Items"),
        ("payments p JOIN orders o ON p.order_id = o.order_id WHERE o.user_id LIKE 'DUMMY%'", "Payments"),
        ("shipments s JOIN orders o ON s.order_id = o.order_id WHERE o.user_id LIKE 'DUMMY%'", "Shipments"),
        ("product_reviews WHERE comment LIKE 'DUMMY%'", "Reviews"),
        ("carts WHERE user_id IN (SELECT user_id FROM users WHERE email LIKE 'DUMMY%')", "Carts"),
        ("cart_items WHERE cart_id IN (SELECT id FROM carts WHERE user_id IN (SELECT user_id FROM users WHERE email LIKE 'DUMMY%'))", "Cart Items"),
        ("inventory WHERE product_id IN (SELECT product_id FROM products WHERE sku LIKE 'DUMMY%')", "Inventory"),
        ("coupons WHERE code LIKE 'DUMMY%'", "Coupons"),
        ("events WHERE session_id LIKE 'DUMMY%'", "Events")
    ]
    
    for table_query, name in tables_to_check:
        cursor.execute(f"SELECT COUNT(*) FROM {table_query}")
        count = cursor.fetchone()[0]
        print(f"{name}: {count:,}")
    
    print("\n✅ DUMMY DATA GENERATION COMPLETE!")
    print("\n📝 To delete all dummy data later, run: python cleanup_dummy_data.py")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    conn.rollback()
    raise
finally:
    cursor.close()
    conn.close()
