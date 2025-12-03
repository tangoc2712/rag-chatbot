#!/usr/bin/env python3
"""
Database migration script for E-commerce RAG Chatbot.
Loads CSV data, generates embeddings via Gemini, and stores in PostgreSQL.
"""
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
from typing import Tuple

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import Settings
from src.database import get_db_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

settings = Settings()


# ============== Data Loading & Preprocessing ==============

def load_datasets(product_path: Path, order_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load and perform initial cleaning of datasets"""
    logger.info("Loading datasets...")
    
    product_df = pd.read_csv(product_path)
    order_df = pd.read_csv(order_path)
    
    logger.info(f"Product CSV columns: {product_df.columns.tolist()}")
    logger.info(f"Order CSV columns: {order_df.columns.tolist()}")
    
    product_df.fillna('', inplace=True)
    order_df.fillna('', inplace=True)
    
    return product_df, order_df


def preprocess_product_data(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess product dataset"""
    logger.info("Preprocessing product data...")
    
    # Create combined text field for semantic search
    df['combined_text'] = (
        df['title'].str.strip() + ' ' +
        df['description'].str.strip() + ' ' +
        df['main_category'].str.strip() + ' ' +
        df['categories'].str.strip()
    )
    
    # Clean numeric fields
    df['Price'] = pd.to_numeric(df['price'], errors='coerce')
    df['Rating'] = pd.to_numeric(df['average_rating'], errors='coerce')
    df['Rating_Count'] = pd.to_numeric(df['rating_number'], errors='coerce')
    
    # Remove products with invalid prices or ratings
    df = df[df['Price'].notna()]
    df = df[df['Rating'].notna()]
    df = df[df['Price'] > 0]
    df = df[df['Rating'].between(0, 5)]
    
    # Create a unique product ID if not present
    if 'Product_ID' not in df.columns:
        df['Product_ID'] = range(1, len(df) + 1)
    
    # Extract features as a list
    df['feature_list'] = df['features'].apply(lambda x: str(x).split('|') if pd.notnull(x) else [])
    
    # Rename columns to match expected schema
    df = df.rename(columns={
        'title': 'Product_Title',
        'main_category': 'Category',
        'description': 'Description',
        'price': 'Price',
        'average_rating': 'Rating',
        'rating_number': 'Rating_Count',
        'store': 'Store',
        'parent_asin': 'Product_ID'
    })
    
    columns_to_keep = [
        'Product_ID', 'Product_Title', 'Description', 'Category',
        'Price', 'Rating', 'Rating_Count', 'Store', 'feature_list',
        'combined_text'
    ]
    
    df = df[columns_to_keep]
    return df


def preprocess_order_data(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess order dataset"""
    logger.info("Preprocessing order data...")
    
    # Convert date and time fields
    df['Order_DateTime'] = pd.to_datetime(df['Order_Date'] + ' ' + df['Time'])
    
    # Clean numeric fields
    numeric_columns = ['Sales', 'Quantity', 'Discount', 'Profit', 'Shipping_Cost']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Remove orders with invalid amounts
    df = df[df['Sales'].notna() & df['Shipping_Cost'].notna()]
    df = df[df['Sales'] > 0]
    
    # Create a unique order ID if not present
    if 'Order_ID' not in df.columns:
        df['Order_ID'] = range(1, len(df) + 1)
    
    # Standardize categorical fields
    df['Order_Priority'] = df['Order_Priority'].str.strip().str.title()
    df['Payment_method'] = df['Payment_method'].str.strip().str.title()
    df['Customer_Login_type'] = df['Customer_Login_type'].str.strip().str.title()
    df['Gender'] = df['Gender'].str.strip().str.title()
    df['Device_Type'] = df['Device_Type'].str.strip().str.title()
    
    # Calculate additional metrics
    df['Total_Amount'] = df['Sales'] * df['Quantity']
    df['Net_Profit'] = df['Profit'] - df['Shipping_Cost']
    
    columns_to_keep = [
        'Order_ID', 'Order_DateTime', 'Customer_Id', 'Gender',
        'Device_Type', 'Customer_Login_type', 'Product_Category',
        'Product', 'Quantity', 'Sales', 'Total_Amount', 'Discount',
        'Profit', 'Net_Profit', 'Shipping_Cost', 'Order_Priority',
        'Payment_method'
    ]
    
    df = df[columns_to_keep]
    return df


# ============== Database Functions ==============

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
    logger.info("Loading and preprocessing data...")
    
    # Load from raw data directory
    product_raw = settings.RAW_DATA_DIR / "Product_Information_Dataset.csv"
    order_raw = settings.RAW_DATA_DIR / "Order_Data_Dataset.csv"
    
    if not product_raw.exists() or not order_raw.exists():
        logger.error(f"Raw data files not found at {settings.RAW_DATA_DIR}")
        return

    product_df, order_df = load_datasets(product_raw, order_raw)
    product_df = preprocess_product_data(product_df)
    product_df = product_df.loc[:, ~product_df.columns.duplicated()]
    product_df['Rating_Count'] = product_df['Rating_Count'].fillna(0).astype(int)
    
    order_df = preprocess_order_data(order_df)
    order_df = order_df.loc[:, ~order_df.columns.duplicated()]
    order_df['Quantity'] = order_df['Quantity'].fillna(0).astype(int)
    
    logger.info(f"Processing {len(product_df)} products and {len(order_df)} orders")
    
    # Generate embeddings
    logger.info("Generating product embeddings...")
    product_embeddings = generate_embeddings(product_df['combined_text'].tolist())
    
    logger.info("Generating order embeddings...")
    order_texts = (
        order_df['Product'] + " " + 
        order_df['Product_Category'] + " " + 
        order_df['Order_Priority']
    ).tolist()
    order_embeddings = generate_embeddings(order_texts)
    
    # Insert into PostgreSQL
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        logger.info("Inserting products...")
        product_data = []
        for (idx, row), embedding in zip(product_df.iterrows(), product_embeddings):
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
    try:
        setup_database()
        migrate_data()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
