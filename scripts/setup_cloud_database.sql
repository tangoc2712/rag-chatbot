-- Cloud PostgreSQL Database Setup for Embedding Generation
-- Execute this script on cloud PostgreSQL: 34.177.103.63:5432

-- =====================================================
-- Step 1: Enable pgvector Extension
-- =====================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- =====================================================
-- Step 2: Add Embedding Columns to All Tables
-- =====================================================

-- Products table
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Categories table
ALTER TABLE categories 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Product reviews table
ALTER TABLE product_reviews 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Orders table
ALTER TABLE orders 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Order items table
ALTER TABLE order_items 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Carts table
ALTER TABLE carts 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Cart items table
ALTER TABLE cart_items 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Payments table
ALTER TABLE payments 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Shipments table
ALTER TABLE shipments 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Inventory table
ALTER TABLE inventory 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Coupons table
ALTER TABLE coupons 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Events table
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Roles table
ALTER TABLE roles 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- =====================================================
-- Step 3: Create Indexes for Vector Similarity Search
-- =====================================================

-- Products embedding index (IVFFlat for approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS products_embedding_idx 
ON products USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Product reviews embedding index
CREATE INDEX IF NOT EXISTS product_reviews_embedding_idx 
ON product_reviews USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Orders embedding index
CREATE INDEX IF NOT EXISTS orders_embedding_idx 
ON orders USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Events embedding index
CREATE INDEX IF NOT EXISTS events_embedding_idx 
ON events USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Users embedding index
CREATE INDEX IF NOT EXISTS users_embedding_idx 
ON users USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- =====================================================
-- Step 4: Verify Schema Updates
-- =====================================================

-- Check all tables have embedding column
SELECT 
    table_name,
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE column_name = 'embedding'
  AND table_schema = 'public'
ORDER BY table_name;

-- =====================================================
-- Step 5: Check Current Embedding Coverage
-- =====================================================

-- Products
SELECT 
    'products' as table_name,
    COUNT(*) as total_records,
    COUNT(embedding) as records_with_embeddings,
    COUNT(*) - COUNT(embedding) as records_without_embeddings
FROM products
UNION ALL
-- Categories
SELECT 
    'categories',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM categories
UNION ALL
-- Product reviews
SELECT 
    'product_reviews',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM product_reviews
UNION ALL
-- Users
SELECT 
    'users',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM users
UNION ALL
-- Orders
SELECT 
    'orders',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM orders
UNION ALL
-- Order items
SELECT 
    'order_items',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM order_items
UNION ALL
-- Carts
SELECT 
    'carts',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM carts
UNION ALL
-- Cart items
SELECT 
    'cart_items',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM cart_items
UNION ALL
-- Payments
SELECT 
    'payments',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM payments
UNION ALL
-- Shipments
SELECT 
    'shipments',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM shipments
UNION ALL
-- Inventory
SELECT 
    'inventory',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM inventory
UNION ALL
-- Coupons
SELECT 
    'coupons',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM coupons
UNION ALL
-- Events
SELECT 
    'events',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM events
UNION ALL
-- Roles
SELECT 
    'roles',
    COUNT(*),
    COUNT(embedding),
    COUNT(*) - COUNT(embedding)
FROM roles;

-- =====================================================
-- Setup Complete!
-- =====================================================
-- Next: Run Airflow DAGs to generate embeddings
