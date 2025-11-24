from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import uuid

from ...rag.assistant import ECommerceRAG
from ...database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    customer_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str

class ChatHistoryResponse(BaseModel):
    history: List[Dict[str, Any]]

# Initialize RAG assistant
rag_assistant = ECommerceRAG()

def save_chat_to_db(session_id: str, customer_id: Optional[str], 
                    user_message: str, bot_response: str, metadata: Optional[Dict] = None):
    """Save chat interaction to database"""
    import json
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Convert metadata dict to JSON string
        metadata_json = json.dumps(metadata) if metadata else json.dumps({})
        
        cur.execute("""
            INSERT INTO chat_history 
            (session_id, customer_id, user_message, bot_response, metadata)
            VALUES (%s, %s, %s, %s, %s::jsonb)
        """, (session_id, customer_id, user_message, bot_response, metadata_json))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving chat to database: {e}")
    finally:
        cur.close()
        conn.close()

@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message to the chatbot and get a response
    """
    try:
        # Generate or use existing session ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # Extract customer ID from message if setting customer
        customer_id = request.customer_id
        user_message = request.message.strip()
        
        # Handle set customer command
        if user_message.lower().startswith('set customer'):
            try:
                customer_id = user_message.split()[-1]
                bot_response = f"Customer ID set to: {customer_id}"
            except (ValueError, IndexError):
                bot_response = "Invalid customer ID. Please use format: 'set customer <id>'"
        else:
            # Process query through RAG assistant
            bot_response = rag_assistant.process_query(
                user_message, 
                int(customer_id) if customer_id and customer_id.isdigit() else None
            )
        
        # Save to database
        save_chat_to_db(
            session_id=session_id,
            customer_id=customer_id,
            user_message=request.message,
            bot_response=bot_response,
            metadata={"source": "web_chat"}
        )
        
        return ChatResponse(
            response=bot_response,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str, limit: int = 50):
    """
    Get chat history for a specific session
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, session_id, customer_id, user_message, bot_response, 
                   timestamp, metadata
            FROM chat_history
            WHERE session_id = %s
            ORDER BY timestamp ASC
            LIMIT %s
        """, (session_id, limit))
        
        rows = cur.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "session_id": row[1],
                "customer_id": row[2],
                "user_message": row[3],
                "bot_response": row[4],
                "timestamp": row[5].isoformat() if row[5] else None,
                "metadata": row[6]
            })
        
        return ChatHistoryResponse(history=history)
        
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/history/customer/{customer_id}", response_model=ChatHistoryResponse)
async def get_customer_chat_history(customer_id: str, limit: int = 100):
    """
    Get all chat history for a specific customer across all sessions
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, session_id, customer_id, user_message, bot_response, 
                   timestamp, metadata
            FROM chat_history
            WHERE customer_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (customer_id, limit))
        
        rows = cur.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "session_id": row[1],
                "customer_id": row[2],
                "user_message": row[3],
                "bot_response": row[4],
                "timestamp": row[5].isoformat() if row[5] else None,
                "metadata": row[6]
            })
        
        return ChatHistoryResponse(history=history)
        
    except Exception as e:
        logger.error(f"Error fetching customer chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.delete("/history/{session_id}")
async def delete_chat_history(session_id: str):
    """
    Delete chat history for a specific session
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM chat_history WHERE session_id = %s
        """, (session_id,))
        conn.commit()
        
        return {"message": f"Chat history deleted for session {session_id}"}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
