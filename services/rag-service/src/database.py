import psycopg2
from psycopg2.extras import RealDictCursor
from .config import Settings
from typing import Optional
from functools import lru_cache
import time
import logging

logger = logging.getLogger(__name__)
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


# Role cache with TTL (Time To Live)
class RoleCache:
    """Simple in-memory cache for user roles with TTL"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self._cache: dict = {}
        self._timestamps: dict = {}
        self._ttl = ttl_seconds
    
    def get(self, user_id: str) -> Optional[str]:
        """Get cached role for user, returns None if expired or not found"""
        if user_id not in self._cache:
            return None
        
        # Check if cache entry has expired
        if time.time() - self._timestamps[user_id] > self._ttl:
            self.invalidate(user_id)
            return None
        
        return self._cache[user_id]
    
    def set(self, user_id: str, role: str):
        """Cache the user's role"""
        self._cache[user_id] = role
        self._timestamps[user_id] = time.time()
    
    def invalidate(self, user_id: str):
        """Remove user from cache"""
        self._cache.pop(user_id, None)
        self._timestamps.pop(user_id, None)
    
    def clear(self):
        """Clear entire cache"""
        self._cache.clear()
        self._timestamps.clear()


# Global role cache instance
_role_cache = RoleCache(ttl_seconds=300)


def get_user_role(user_id: str) -> str:
    """
    Get user role from database with caching.
    Returns 'user' as default if user not found.
    
    Args:
        user_id: The user's ID (uid field in users table)
    
    Returns:
        str: User's role ('admin' or 'user')
    """
    if not user_id:
        return 'user'
    
    # Check cache first
    cached_role = _role_cache.get(user_id)
    if cached_role is not None:
        logger.debug(f"Role cache hit for user {user_id}: {cached_role}")
        return cached_role
    
    # Query database
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT role FROM "user" 
                WHERE uid = %s OR user_id::text = %s
                LIMIT 1
            """, (user_id, user_id))
            result = cur.fetchone()
            
            if result and result.get('role'):
                role = result['role']
            else:
                role = 'user'  # Default role
            
            # Cache the result
            _role_cache.set(user_id, role)
            logger.debug(f"Cached role for user {user_id}: {role}")
            
            return role
    except Exception as e:
        logger.error(f"Error fetching user role: {e}")
        return 'user'  # Default to user on error
    finally:
        conn.close()


def invalidate_role_cache(user_id: str):
    """Invalidate cached role for a user (call when role is updated)"""
    _role_cache.invalidate(user_id)


def clear_role_cache():
    """Clear the entire role cache"""
    _role_cache.clear()
