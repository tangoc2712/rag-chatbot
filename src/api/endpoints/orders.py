from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from ...database import get_db_connection, get_db_cursor

router = APIRouter()

@router.get("/customer/{customer_id}", response_model=List[Dict[str, Any]])
async def get_customer_orders(
    customer_id: int,
    limit: int = Query(default=10, ge=1, le=100)
):
    """Retrieve orders for a specific customer"""
    conn = get_db_connection()
    try:
        with get_db_cursor(conn) as cur:
            cur.execute("""
                SELECT * FROM \"order\" 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (str(customer_id), limit))
            orders = cur.fetchall()
            
            if not orders:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No orders found for customer {customer_id}"
                )
            return orders
    finally:
        conn.close()

@router.get("/priority/{priority}", response_model=List[Dict[str, Any]])
async def get_orders_by_priority(
    priority: str,
    limit: int = Query(default=10, ge=1, le=100)
):
    """Retrieve orders by priority level"""
    conn = get_db_connection()
    try:
        with get_db_cursor(conn) as cur:
            cur.execute("""
                SELECT * FROM \"order\" 
                WHERE LOWER(status) = LOWER(%s)
                ORDER BY created_at DESC 
                LIMIT %s
            """, (priority, limit))
            orders = cur.fetchall()
            
            if not orders:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No orders found with status {priority}"
                )
            return orders
    finally:
        conn.close()
