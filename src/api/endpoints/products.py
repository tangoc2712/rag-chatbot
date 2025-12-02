from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from ...database import get_db_connection, get_db_cursor
from ...config import Settings

router = APIRouter()
settings = Settings()

# Initialize Gemini
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

@router.get("/search", response_model=List[Dict[str, Any]])
async def search_products(
    query: str = Query(..., min_length=2),
    category: Optional[str] = None,
    min_rating: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Search products using semantic search with filters
    """
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google API Key not configured")

    try:
        # Generate embedding
        result = genai.embed_content(
            model="models/embedding-001",
            content=query,
            task_type="retrieval_query"
        )
        query_embedding = result['embedding']
        
        conn = get_db_connection()
        try:
            with get_db_cursor(conn) as cur:
                # Build Query
                sql = """
                    SELECT *, embedding <=> %s::vector as distance 
                    FROM product 
                    WHERE 1=1
                """
                params = [query_embedding]
                
                if category:
                    sql += " AND category ILIKE %s"
                    params.append(f"%{category}%")
                
                if min_rating is not None:
                    sql += " AND rating >= %s"
                    params.append(min_rating)
                    
                if max_price is not None:
                    sql += " AND price <= %s"
                    params.append(max_price)
                
                sql += " ORDER BY distance ASC LIMIT %s"
                params.append(limit)
                
                cur.execute(sql, params)
                products = cur.fetchall()
                
                return products
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
