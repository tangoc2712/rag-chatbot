from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from ...database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/payments")
async def get_payments(limit: int = 50, status: Optional[str] = None):
    """Get all payments with optional status filter"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT p.*, o.user_id, o.total_amount as order_total
            FROM payments p
            LEFT JOIN orders o ON p.order_id = o.order_id
        """
        params = []
        
        if status:
            query += " WHERE p.payment_status = %s"
            params.append(status)
        
        query += " ORDER BY p.payment_date DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        payments = [dict(zip(columns, row)) for row in rows]
        return {"payments": payments, "count": len(payments)}
        
    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/payments/order/{order_id}")
async def get_order_payment(order_id: int):
    """Get payment for a specific order"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT * FROM payments WHERE order_id = %s
            ORDER BY payment_date DESC
        """, (order_id,))
        
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        payments = [dict(zip(columns, row)) for row in rows]
        return {"payments": payments, "count": len(payments)}
        
    except Exception as e:
        logger.error(f"Error fetching order payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/payments/transaction/{transaction_id}")
async def get_payment_by_transaction(transaction_id: str):
    """Get payment by transaction ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT p.*, o.user_id
            FROM payments p
            LEFT JOIN orders o ON p.order_id = o.order_id
            WHERE p.transaction_id = %s
        """, (transaction_id,))
        
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return dict(zip(columns, row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
