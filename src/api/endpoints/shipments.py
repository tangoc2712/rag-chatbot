from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from ...database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/shipments")
async def get_shipments(limit: int = 50, status: Optional[str] = None):
    """Get all shipments with optional status filter"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT s.*, o.user_id, o.total_amount
            FROM shipments s
            LEFT JOIN orders o ON s.order_id = o.order_id
        """
        params = []
        
        if status:
            query += " WHERE s.status = %s"
            params.append(status)
        
        query += " ORDER BY s.shipment_date DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        shipments = [dict(zip(columns, row)) for row in rows]
        return {"shipments": shipments, "count": len(shipments)}
        
    except Exception as e:
        logger.error(f"Error fetching shipments: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/shipments/tracking/{tracking_number}")
async def track_shipment(tracking_number: str):
    """Track shipment by tracking number"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT s.*, o.user_id, o.total_amount, o.status as order_status
            FROM shipments s
            LEFT JOIN orders o ON s.order_id = o.order_id
            WHERE s.tracking_number = %s
        """, (tracking_number,))
        
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Shipment not found")
        
        return dict(zip(columns, row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking shipment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/shipments/order/{order_id}")
async def get_order_shipment(order_id: int):
    """Get shipment for a specific order"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT * FROM shipments WHERE order_id = %s
            ORDER BY shipment_date DESC
        """, (order_id,))
        
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        shipments = [dict(zip(columns, row)) for row in rows]
        return {"shipments": shipments, "count": len(shipments)}
        
    except Exception as e:
        logger.error(f"Error fetching order shipment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
