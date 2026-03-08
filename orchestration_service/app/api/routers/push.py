from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging
import psycopg2
from app.core.database import get_db_connection
from app.core.vapid import get_vapid_public_key

router = APIRouter()
logger = logging.getLogger(__name__)

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict

@router.get("/vapid-public-key")
def get_public_key():
    return {"public_key": get_vapid_public_key()}

@router.post("/subscribe")
def subscribe(subscription: PushSubscription):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        endpoint = subscription.endpoint
        p256dh = subscription.keys.get("p256dh")
        auth = subscription.keys.get("auth")
        
        cur.execute("""
            INSERT INTO push_subscriptions (endpoint, p256dh, auth) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (endpoint) DO UPDATE 
            SET p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth
        """, (endpoint, p256dh, auth))
        
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "message": "Subscription saved"}
    except psycopg2.Error as e:
        logger.error(f"DB Error saving push subscription: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error saving push subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))
