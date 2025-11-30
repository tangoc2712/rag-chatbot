from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from ...database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/categories")
async def get_categories(is_active: Optional[bool] = None):
    """Get all categories"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = "SELECT * FROM categories"
        params = []
        
        if is_active is not None:
            query += " WHERE is_active = %s"
            params.append(is_active)
        
        query += " ORDER BY category_name"
        
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        categories = [dict(zip(columns, row)) for row in rows]
        return {"categories": categories, "count": len(categories)}
        
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/categories/{category_id}")
async def get_category(category_id: int):
    """Get specific category by ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM categories WHERE category_id = %s", (category_id,))
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return dict(zip(columns, row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching category: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/categories/{category_id}/products")
async def get_category_products(category_id: int, limit: int = 50):
    """Get all products in a category"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT * FROM products
            WHERE category_id = %s AND is_active = true
            ORDER BY created_at DESC
            LIMIT %s
        """, (category_id, limit))
        
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        products = [dict(zip(columns, row)) for row in rows]
        return {"products": products, "count": len(products)}
        
    except Exception as e:
        logger.error(f"Error fetching category products: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
