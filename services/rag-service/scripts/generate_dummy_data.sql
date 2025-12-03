-- ============================================================================
-- DUMMY DATA GENERATION SCRIPT FOR ECOMMERCE RAG CHATBOT
-- ============================================================================
-- Purpose: Generate 10,000 dummy orders with all related tables
-- Identification: All dummy data has email/name containing 'DUMMY_' prefix
-- Deletion: Use cleanup_dummy_data.sql to remove all dummy records
-- ============================================================================

-- Start transaction
BEGIN;

-- ============================================================================
-- 1. CREATE DUMMY USERS (1,000 users for 10k orders)
-- ============================================================================
INSERT INTO users (user_id, email, full_name, phone, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    'DUMMY_user' || i || '@test.com',
    'DUMMY User ' || i,
    '+1-555-' || LPAD(i::text, 7, '0'),
    CURRENT_TIMESTAMP - (random() * INTERVAL '365 days'),
    CURRENT_TIMESTAMP
FROM generate_series(1, 1000) AS i;

-- ============================================================================
-- 2. CREATE DUMMY CATEGORIES (10 additional categories)
-- ============================================================================
INSERT INTO categories (name, description, type, parent_category_id, created_at, updated_at)
VALUES
    ('DUMMY Electronics', 'DUMMY category for electronics', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Clothing', 'DUMMY category for clothing', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Books', 'DUMMY category for books', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Home', 'DUMMY category for home goods', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Sports', 'DUMMY category for sports equipment', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Toys', 'DUMMY category for toys', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Food', 'DUMMY category for food items', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Beauty', 'DUMMY category for beauty products', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Automotive', 'DUMMY category for automotive', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('DUMMY Garden', 'DUMMY category for garden supplies', 'product_category', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- ============================================================================
-- 3. CREATE DUMMY PRODUCTS (2,000 products)
-- ============================================================================
WITH dummy_categories AS (
    SELECT category_id FROM categories WHERE name LIKE 'DUMMY%'
)
INSERT INTO products (product_id, sku, name, description, price, currency, category_id, is_active, sale_price, product_url, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    'DUMMY-SKU-' || LPAD(i::text, 6, '0'),
    'DUMMY Product ' || i,
    'DUMMY This is a test product number ' || i || ' for demonstration purposes. High quality and affordable.',
    (random() * 1000 + 10)::numeric(10,2),
    'USD',
    (SELECT category_id FROM dummy_categories ORDER BY random() LIMIT 1),
    true,
    NULL,
    'https://dummy.example.com/product/' || i,
    CURRENT_TIMESTAMP - (random() * INTERVAL '180 days'),
    CURRENT_TIMESTAMP
FROM generate_series(1, 2000) AS i;

-- ============================================================================
-- 4. CREATE DUMMY ORDERS (10,000 orders)
-- ============================================================================
WITH dummy_users AS (
    SELECT user_id FROM users WHERE email LIKE 'DUMMY%'
)
INSERT INTO orders (order_id, user_id, status, total_amount, currency, shipping_address, billing_address, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    (SELECT user_id FROM dummy_users ORDER BY random() LIMIT 1),
    (ARRAY['pending', 'processing', 'shipped', 'delivered', 'cancelled'])[floor(random() * 5 + 1)],
    (random() * 500 + 20)::numeric(10,2),
    'USD',
    'DUMMY ' || i || ' Main St, City, ST 12345',
    'DUMMY ' || i || ' Billing Ave, Town, ST 54321',
    CURRENT_TIMESTAMP - (random() * INTERVAL '90 days'),
    CURRENT_TIMESTAMP
FROM generate_series(1, 10000) AS i;

-- ============================================================================
-- 5. CREATE DUMMY ORDER ITEMS (25,000 items - avg 2.5 items per order)
-- ============================================================================
WITH dummy_orders AS (
    SELECT order_id FROM orders WHERE shipping_address LIKE 'DUMMY%'
),
dummy_products AS (
    SELECT product_id, price FROM products WHERE sku LIKE 'DUMMY%'
)
INSERT INTO order_items (order_item_id, order_id, product_id, quantity, price, currency, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    o.order_id,
    (SELECT product_id FROM dummy_products ORDER BY random() LIMIT 1),
    floor(random() * 5 + 1)::integer,
    p.price,
    'USD',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM dummy_orders o
CROSS JOIN LATERAL (SELECT 1 FROM generate_series(1, floor(random() * 4 + 1)::integer)) AS items
CROSS JOIN LATERAL (SELECT price FROM dummy_products ORDER BY random() LIMIT 1) AS p;

-- ============================================================================
-- 6. CREATE DUMMY PAYMENTS (10,000 payments - 1 per order)
-- ============================================================================
WITH dummy_orders AS (
    SELECT order_id, total_amount, currency FROM orders WHERE shipping_address LIKE 'DUMMY%'
)
INSERT INTO payments (payment_id, order_id, payment_method, amount, currency, status, transaction_id, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    order_id,
    (ARRAY['credit_card', 'debit_card', 'paypal', 'bank_transfer'])[floor(random() * 4 + 1)],
    total_amount,
    currency,
    (ARRAY['pending', 'completed', 'failed', 'refunded'])[floor(random() * 4 + 1)],
    'DUMMY-TXN-' || gen_random_uuid()::text,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM dummy_orders;

-- ============================================================================
-- 7. CREATE DUMMY SHIPMENTS (8,000 shipments - 80% of orders)
-- ============================================================================
WITH dummy_orders AS (
    SELECT order_id FROM orders WHERE shipping_address LIKE 'DUMMY%' AND status IN ('shipped', 'delivered')
)
INSERT INTO shipments (shipment_id, order_id, tracking_number, carrier, status, shipped_at, delivered_at, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    order_id,
    'DUMMY-TRACK-' || UPPER(substring(md5(random()::text), 1, 12)),
    (ARRAY['FedEx', 'UPS', 'USPS', 'DHL'])[floor(random() * 4 + 1)],
    (ARRAY['in_transit', 'delivered', 'returned'])[floor(random() * 3 + 1)],
    CURRENT_TIMESTAMP - (random() * INTERVAL '30 days'),
    CASE WHEN random() > 0.3 THEN CURRENT_TIMESTAMP - (random() * INTERVAL '15 days') ELSE NULL END,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM dummy_orders;

-- ============================================================================
-- 8. CREATE DUMMY PRODUCT REVIEWS (5,000 reviews - 50% of orders)
-- ============================================================================
WITH dummy_users AS (
    SELECT user_id FROM users WHERE email LIKE 'DUMMY%'
),
dummy_products AS (
    SELECT product_id FROM products WHERE sku LIKE 'DUMMY%'
)
INSERT INTO product_reviews (review_id, product_id, user_id, rating, review_text, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    (SELECT product_id FROM dummy_products ORDER BY random() LIMIT 1),
    (SELECT user_id FROM dummy_users ORDER BY random() LIMIT 1),
    floor(random() * 5 + 1)::integer,
    'DUMMY Review: ' || (ARRAY[
        'Great product, highly recommended!',
        'Good value for money.',
        'Satisfied with the purchase.',
        'Could be better, but acceptable.',
        'Not what I expected.',
        'Excellent quality!',
        'Fast shipping and good packaging.',
        'Average product, nothing special.'
    ])[floor(random() * 8 + 1)],
    CURRENT_TIMESTAMP - (random() * INTERVAL '60 days'),
    CURRENT_TIMESTAMP
FROM generate_series(1, 5000) AS i;

-- ============================================================================
-- 9. CREATE DUMMY CARTS (500 active carts)
-- ============================================================================
WITH dummy_users AS (
    SELECT user_id FROM users WHERE email LIKE 'DUMMY%' LIMIT 500
)
INSERT INTO carts (cart_id, user_id, status, total_amount, currency, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    user_id,
    (ARRAY['active', 'abandoned', 'converted'])[floor(random() * 3 + 1)],
    (random() * 300 + 10)::numeric(10,2),
    'USD',
    CURRENT_TIMESTAMP - (random() * INTERVAL '7 days'),
    CURRENT_TIMESTAMP
FROM dummy_users;

-- ============================================================================
-- 10. CREATE DUMMY CART ITEMS (1,500 cart items)
-- ============================================================================
WITH dummy_carts AS (
    SELECT cart_id FROM carts WHERE total_amount IS NOT NULL AND cart_id IN (
        SELECT cart_id FROM carts c 
        JOIN users u ON c.user_id = u.user_id 
        WHERE u.email LIKE 'DUMMY%'
    )
),
dummy_products AS (
    SELECT product_id, price FROM products WHERE sku LIKE 'DUMMY%'
)
INSERT INTO cart_items (cart_item_id, cart_id, product_id, quantity, price, currency, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    c.cart_id,
    (SELECT product_id FROM dummy_products ORDER BY random() LIMIT 1),
    floor(random() * 3 + 1)::integer,
    p.price,
    'USD',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM dummy_carts c
CROSS JOIN LATERAL (SELECT 1 FROM generate_series(1, floor(random() * 4 + 1)::integer)) AS items
CROSS JOIN LATERAL (SELECT price FROM dummy_products ORDER BY random() LIMIT 1) AS p;

-- ============================================================================
-- 11. CREATE DUMMY INVENTORY (2,000 inventory records - 1 per product)
-- ============================================================================
WITH dummy_products AS (
    SELECT product_id FROM products WHERE sku LIKE 'DUMMY%'
)
INSERT INTO inventory (inventory_id, product_id, warehouse_location, quantity, reserved_quantity, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    product_id,
    'DUMMY-WH-' || (ARRAY['NY', 'LA', 'CHI', 'HOU', 'PHX'])[floor(random() * 5 + 1)],
    floor(random() * 1000 + 50)::integer,
    floor(random() * 50)::integer,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM dummy_products;

-- ============================================================================
-- 12. CREATE DUMMY COUPONS (100 coupons)
-- ============================================================================
INSERT INTO coupons (coupon_id, code, discount_type, discount_value, min_purchase_amount, max_discount_amount, valid_from, valid_to, is_active, usage_limit, times_used, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    'DUMMY-' || UPPER(substring(md5(i::text), 1, 8)),
    (ARRAY['percentage', 'fixed_amount'])[floor(random() * 2 + 1)],
    (random() * 50 + 5)::numeric(10,2),
    20.00,
    100.00,
    CURRENT_TIMESTAMP - INTERVAL '30 days',
    CURRENT_TIMESTAMP + INTERVAL '60 days',
    true,
    floor(random() * 500 + 100)::integer,
    floor(random() * 50)::integer,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM generate_series(1, 100) AS i;

-- ============================================================================
-- 13. CREATE DUMMY EVENTS (20,000 events - 2 per order)
-- ============================================================================
WITH dummy_users AS (
    SELECT user_id FROM users WHERE email LIKE 'DUMMY%'
)
INSERT INTO events (event_id, event_type, user_id, metadata, created_at)
SELECT 
    gen_random_uuid(),
    (ARRAY['page_view', 'add_to_cart', 'checkout', 'purchase', 'search', 'login', 'logout'])[floor(random() * 7 + 1)],
    (SELECT user_id FROM dummy_users ORDER BY random() LIMIT 1),
    jsonb_build_object(
        'dummy', true,
        'session_id', 'DUMMY-SESSION-' || gen_random_uuid()::text,
        'timestamp', CURRENT_TIMESTAMP
    ),
    CURRENT_TIMESTAMP - (random() * INTERVAL '30 days')
FROM generate_series(1, 20000) AS i;

-- ============================================================================
-- 14. VERIFY DUMMY DATA COUNTS
-- ============================================================================
DO $$
DECLARE
    v_users INTEGER;
    v_categories INTEGER;
    v_products INTEGER;
    v_orders INTEGER;
    v_order_items INTEGER;
    v_payments INTEGER;
    v_shipments INTEGER;
    v_reviews INTEGER;
    v_carts INTEGER;
    v_cart_items INTEGER;
    v_inventory INTEGER;
    v_coupons INTEGER;
    v_events INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_users FROM users WHERE email LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_categories FROM categories WHERE name LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_products FROM products WHERE sku LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_orders FROM orders WHERE shipping_address LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_order_items FROM order_items WHERE order_id IN (SELECT order_id FROM orders WHERE shipping_address LIKE 'DUMMY%');
    SELECT COUNT(*) INTO v_payments FROM payments WHERE transaction_id LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_shipments FROM shipments WHERE tracking_number LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_reviews FROM product_reviews WHERE review_text LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_carts FROM carts WHERE user_id IN (SELECT user_id FROM users WHERE email LIKE 'DUMMY%');
    SELECT COUNT(*) INTO v_cart_items FROM cart_items WHERE cart_id IN (SELECT cart_id FROM carts WHERE user_id IN (SELECT user_id FROM users WHERE email LIKE 'DUMMY%'));
    SELECT COUNT(*) INTO v_inventory FROM inventory WHERE warehouse_location LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_coupons FROM coupons WHERE code LIKE 'DUMMY%';
    SELECT COUNT(*) INTO v_events FROM events WHERE metadata->>'dummy' = 'true';
    
    RAISE NOTICE 'DUMMY DATA GENERATION COMPLETE:';
    RAISE NOTICE '  Users: %', v_users;
    RAISE NOTICE '  Categories: %', v_categories;
    RAISE NOTICE '  Products: %', v_products;
    RAISE NOTICE '  Orders: %', v_orders;
    RAISE NOTICE '  Order Items: %', v_order_items;
    RAISE NOTICE '  Payments: %', v_payments;
    RAISE NOTICE '  Shipments: %', v_shipments;
    RAISE NOTICE '  Reviews: %', v_reviews;
    RAISE NOTICE '  Carts: %', v_carts;
    RAISE NOTICE '  Cart Items: %', v_cart_items;
    RAISE NOTICE '  Inventory: %', v_inventory;
    RAISE NOTICE '  Coupons: %', v_coupons;
    RAISE NOTICE '  Events: %', v_events;
END $$;

-- Commit transaction
COMMIT;

-- ============================================================================
-- DELETION FORMULA (for future cleanup)
-- ============================================================================
-- Run cleanup_dummy_data.sql to remove all dummy records
-- Identifier patterns:
--   - users: email LIKE 'DUMMY%'
--   - categories: name LIKE 'DUMMY%'
--   - products: sku LIKE 'DUMMY%'
--   - orders: shipping_address LIKE 'DUMMY%'
--   - payments: transaction_id LIKE 'DUMMY%'
--   - shipments: tracking_number LIKE 'DUMMY%'
--   - reviews: review_text LIKE 'DUMMY%'
--   - inventory: warehouse_location LIKE 'DUMMY%'
--   - coupons: code LIKE 'DUMMY%'
--   - events: metadata->>'dummy' = 'true'
--   - Related items via foreign keys
-- ============================================================================
