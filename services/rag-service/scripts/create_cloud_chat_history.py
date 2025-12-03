#!/usr/bin/env python3
"""
Create chat_history table in Cloud PostgreSQL database
Execute this to add chat history tracking to your cloud database
"""
import sys
from pathlib import Path
import logging
import psycopg2

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_cloud_chat_history_table():
    """Create chat_history table on cloud PostgreSQL"""
    settings = Settings()
    
    # Connect to cloud database
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME
    )
    cur = conn.cursor()
    
    try:
        logger.info(f"Connected to cloud database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        
        # Create chat_history table
        logger.info("Creating chat_history table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                customer_id TEXT,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            );
        """)
        
        # Create indexes for faster queries
        logger.info("Creating indexes...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_history_session_id 
            ON chat_history(session_id);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_history_customer_id 
            ON chat_history(customer_id);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp 
            ON chat_history(timestamp);
        """)
        
        conn.commit()
        logger.info("✅ Chat history table created successfully on cloud database!")
        
        # Verify table creation
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'chat_history'
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()
        
        logger.info("\nTable structure:")
        for col in columns:
            logger.info(f"  - {col[0]}: {col[1]}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error creating chat history table: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_cloud_chat_history_table()
