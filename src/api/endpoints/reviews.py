from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from ...database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/reviews")
async def get_reviews(limit: int = 50, min_rating: Optional[int] = None):
    """Get product reviews with optional rating filter"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT pr.*, p.name as product_name, u.full_name as reviewer_name
            FROM product_reviews pr
            LEFT JOIN products p ON pr.product_id = p.product_id
            LEFT JOIN users u ON pr.user_id = u.user_id
        """
        params = []
        
        if min_rating is not None:
            query += " WHERE pr.rating >= %s"
            params.append(min_rating)
        
        query += " ORDER BY pr.review_date DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        reviews = [dict(zip(columns, row)) for row in rows]
        return {"reviews": reviews, "count": len(reviews)}
        
    except Exception as e:
        logger.error(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/reviews/product/{product_id}")
async def get_product_reviews(product_id: int, limit: int = 50):
    """Get all reviews for a specific product"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT pr.*, u.full_name as reviewer_name
            FROM product_reviews pr
            LEFT JOIN users u ON pr.user_id = u.user_id
            WHERE pr.product_id = %s
            ORDER BY pr.review_date DESC
            LIMIT %s
        """, (product_id, limit))
        
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        reviews = [dict(zip(columns, row)) for row in rows]
        
        # Get average rating
        cur.execute("""
            SELECT AVG(rating)::numeric(3,2) as avg_rating, COUNT(*) as total_reviews
            FROM product_reviews
            WHERE product_id = %s
        """, (product_id,))
        stats = cur.fetchone()
        
        return {
            "reviews": reviews,
            "count": len(reviews),
            "avg_rating": float(stats[0]) if stats[0] else 0,
            "total_reviews": stats[1]
        }
        
    except Exception as e:
        logger.error(f"Error fetching product reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
