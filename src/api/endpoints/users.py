from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging

from ...database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/users")
async def get_users(limit: int = 50, is_active: Optional[bool] = None):
    """Get all users with optional filters"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = "SELECT * FROM \"user\""
        params = []
        
        if is_active is not None:
            query += " WHERE is_active = %s"
            params.append(is_active)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        users = [dict(zip(columns, row)) for row in rows]
        return {"users": users, "count": len(users)}
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get specific user by ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM \"user\" WHERE user_id = %s", (user_id,))
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return dict(zip(columns, row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/users/{user_id}/orders")
async def get_user_orders(user_id: int, limit: int = 20):
    """Get all orders for a specific user"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT o.*, COUNT(oi.order_item_id) as item_count
            FROM \"order\" o
            LEFT JOIN order_item oi ON o.order_id = oi.order_id
            WHERE o.user_id = %s
            GROUP BY o.order_id
            ORDER BY o.created_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        orders = [dict(zip(columns, row)) for row in rows]
        return {"orders": orders, "count": len(orders)}
        
    except Exception as e:
        logger.error(f"Error fetching user orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
