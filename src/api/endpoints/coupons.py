from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from ...database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/coupons")
async def get_coupons(active_only: bool = True):
    """Get all coupons"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = "SELECT * FROM coupon"
        
        if active_only:
            query += " WHERE valid_to >= CURRENT_TIMESTAMP"
        
        query += " ORDER BY created_at DESC"
        
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        coupons = [dict(zip(columns, row)) for row in rows]
        return {"coupons": coupons, "count": len(coupons)}
        
    except Exception as e:
        logger.error(f"Error fetching coupons: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/coupons/{coupon_code}")
async def get_coupon_by_code(coupon_code: str):
    """Get coupon by code"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT * FROM coupon 
            WHERE code = %s AND valid_to >= CURRENT_TIMESTAMP
        """, (coupon_code,))
        
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Coupon not found or expired")
        
        return dict(zip(columns, row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching coupon: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
