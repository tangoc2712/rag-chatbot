#!/usr/bin/env python3
"""
Create chat history table in PostgreSQL database
"""
import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_chat_history_table():
    """Create chat_history table"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create chat_history table
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
        logger.info("✅ Chat history table created successfully!")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error creating chat history table: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_chat_history_table()
