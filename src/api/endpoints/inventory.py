from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from ...database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/inventory")
async def get_inventory(limit: int = 100, low_stock: Optional[bool] = None):
    """Get inventory with optional low stock filter"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT i.*, p.name as product_name, p.sku
            FROM inventory i
            LEFT JOIN products p ON i.product_id = p.product_id
        """
        params = []
        
        if low_stock:
            query += " WHERE i.quantity_available < 10"
        
        query += " ORDER BY i.quantity_available ASC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        inventory = [dict(zip(columns, row)) for row in rows]
        return {"inventory": inventory, "count": len(inventory)}
        
    except Exception as e:
        logger.error(f"Error fetching inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/inventory/product/{product_id}")
async def get_product_inventory(product_id: int):
    """Get inventory for a specific product"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT i.*, p.name as product_name
            FROM inventory i
            LEFT JOIN products p ON i.product_id = p.product_id
            WHERE i.product_id = %s
        """, (product_id,))
        
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Inventory not found for this product")
        
        return dict(zip(columns, row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
