import psycopg2
from psycopg2.extras import RealDictCursor
from .config import Settings

settings = Settings()

def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME
    )

def get_db_cursor(conn):
    """Get a cursor that returns dictionaries"""
    return conn.cursor(cursor_factory=RealDictCursor)
