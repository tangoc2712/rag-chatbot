#!/usr/bin/env python3
import os
import sys
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import google.generativeai as genai
from pathlib import Path
import logging
import time

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import Settings
from scripts.preprocess_data import load_datasets, preprocess_product_data, preprocess_order_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

settings = Settings()

def get_db_connection():
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME
    )

def setup_database():
    """Create tables with vector extension"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create Products table
        cur.execute("""
            DROP TABLE IF EXISTS products CASCADE;
            CREATE TABLE products (
                product_id TEXT PRIMARY KEY,
                product_title TEXT,
                description TEXT,
                category TEXT,
                price FLOAT,
                rating FLOAT,
                rating_count INTEGER,
                store TEXT,
                feature_list TEXT[],
                combined_text TEXT,
                embedding vector(768)
            );
        """)
        
        # Create Orders table
        cur.execute("""
            DROP TABLE IF EXISTS orders CASCADE;
            CREATE TABLE orders (
                order_id TEXT PRIMARY KEY,
                order_datetime TIMESTAMP,
                customer_id TEXT,
                gender TEXT,
                device_type TEXT,
                customer_login_type TEXT,
                product_category TEXT,
                product TEXT,
                quantity INTEGER,
                sales FLOAT,
                total_amount FLOAT,
                discount FLOAT,
                profit FLOAT,
                net_profit FLOAT,
                shipping_cost FLOAT,
                order_priority TEXT,
                payment_method TEXT,
                embedding vector(768)
            );
        """)
        
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error setting up database: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def generate_embeddings(text_list, batch_size=100):
    """Generate embeddings using Google Gemini"""
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set in configuration")
        
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    
    embeddings = []
    total = len(text_list)
    
    for i in range(0, total, batch_size):
        batch = text_list[i:i + batch_size]
        try:
            # Gemini embedding model
            result = genai.embed_content(
                model="models/embedding-001",
                content=batch,
                task_type="retrieval_document",
                title="Embedding of ecommerce data"
            )
            embeddings.extend(result['embedding'])
            logger.info(f"Processed {min(i + batch_size, total)}/{total} embeddings")
            time.sleep(1) # Rate limiting
        except Exception as e:
            logger.error(f"Error generating embeddings for batch {i}: {e}")
            # Fallback or retry logic could go here
            raise
            
    return embeddings

def migrate_data():
    """Main migration function"""
    # 1. Load and Preprocess Data
    logger.info("Loading and preprocessing data...")
    # We use the raw paths from config to ensure we start fresh or use existing logic
    # Note: load_datasets expects paths, so we use the ones from settings
    # But settings.PRODUCT_DATA_PATH might point to processed. 
    # Let's use RAW_DATA_DIR to be safe if we want to re-process, 
    # or just use the load_datasets logic which handles raw files.
    
    # Actually, let's look at how load_datasets is called in preprocess_data.py
    # It takes product_path and order_path.
    # We should probably use the raw files to ensure we have the source of truth.
    product_raw = settings.RAW_DATA_DIR / "Product_Information_Dataset.csv"
    order_raw = settings.RAW_DATA_DIR / "Order_Data_Dataset.csv"
    
    if not product_raw.exists() or not order_raw.exists():
        logger.error(f"Raw data files not found at {settings.RAW_DATA_DIR}")
        return

    product_df, order_df = load_datasets(product_raw, order_raw)
    product_df = preprocess_product_data(product_df)
    # Fix potential duplicate columns from preprocessing
    product_df = product_df.loc[:, ~product_df.columns.duplicated()]
    # Ensure integer columns don't have NaNs
    product_df['Rating_Count'] = product_df['Rating_Count'].fillna(0).astype(int)
    
    order_df = preprocess_order_data(order_df)
    order_df = order_df.loc[:, ~order_df.columns.duplicated()]
    # Ensure integer columns don't have NaNs
    order_df['Quantity'] = order_df['Quantity'].fillna(0).astype(int)
    
    # Limit data for testing if needed (optional, but good for "dummy a bunch of data")
    # The user said "dummy a bunch of data", implying maybe not all of it? 
    # But usually migration means all. I'll stick to all for now, or maybe top 1000 if it's huge.
    # The dataset seems to be ~3k products and ~50k orders. 3k is fine. 50k might take a while for embeddings.
    # Let's limit orders to 1000 for now to save API quota/time, or ask user. 
    # I'll process all products (critical for RAG) and maybe a subset of orders?
    # For now, I'll process all products and top 1000 orders to be safe on quota.
    
    logger.info(f"Processing {len(product_df)} products and {len(order_df)} orders")
    
    # 2. Generate Embeddings
    logger.info("Generating product embeddings...")
    product_embeddings = generate_embeddings(product_df['combined_text'].tolist())
    
    logger.info("Generating order embeddings...")
    # Create text representation for orders
    order_texts = (
        order_df['Product'] + " " + 
        order_df['Product_Category'] + " " + 
        order_df['Order_Priority']
    ).tolist()
    # Limit orders to 500 for this demo to avoid hitting rate limits hard
    order_limit = 500
    order_df = order_df.head(order_limit)
    order_texts = order_texts[:order_limit]
    
    order_embeddings = generate_embeddings(order_texts)
    
    # 3. Insert into Postgres
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Insert Products
        logger.info("Inserting products...")
        product_data = []
        for (idx, row), embedding in zip(product_df.iterrows(), product_embeddings):
            # feature_list is a list, we need to ensure it's formatted for Postgres array
            # psycopg2 handles lists automatically
            product_data.append((
                str(row['Product_ID']),
                row['Product_Title'],
                row['Description'],
                row['Category'],
                float(row['Price']),
                float(row['Rating']),
                int(row['Rating_Count']),
                row['Store'],
                row['feature_list'],
                row['combined_text'],
                embedding
            ))
            
        execute_values(cur, """
            INSERT INTO products (
                product_id, product_title, description, category, price, 
                rating, rating_count, store, feature_list, combined_text, embedding
            ) VALUES %s
        """, product_data)
        
        # Insert Orders
        logger.info("Inserting orders...")
        order_data = []
        for (idx, row), embedding in zip(order_df.iterrows(), order_embeddings):
            order_data.append((
                str(row['Order_ID']),
                row['Order_DateTime'],
                str(row['Customer_Id']),
                row['Gender'],
                row['Device_Type'],
                row['Customer_Login_type'],
                row['Product_Category'],
                row['Product'],
                int(row['Quantity']),
                float(row['Sales']),
                float(row['Total_Amount']),
                float(row['Discount']),
                float(row['Profit']),
                float(row['Net_Profit']),
                float(row['Shipping_Cost']),
                row['Order_Priority'],
                row['Payment_method'],
                embedding
            ))
            
        execute_values(cur, """
            INSERT INTO orders (
                order_id, order_datetime, customer_id, gender, device_type,
                customer_login_type, product_category, product, quantity,
                sales, total_amount, discount, profit, net_profit,
                shipping_cost, order_priority, payment_method, embedding
            ) VALUES %s
        """, order_data)
        
        conn.commit()
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting data: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Wait for DB to be ready
    time.sleep(5)
    try:
        setup_database()
        migrate_data()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
