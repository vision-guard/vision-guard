from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import UserCreate, UserLogin
from app.core.database import get_db_connection
from app.core.security import hash_password
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register")
def register_user(user: UserCreate):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")
        
        pw_hash = hash_password(user.password)
        # Registering explicitly as UNASSIGNED so Admin must give them permissions
        cur.execute(
            "INSERT INTO users (username, password_hash, email, phone, role) VALUES (%s, %s, %s, %s, 'UNASSIGNED')",
            (user.username, pw_hash, user.email, user.phone)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "User registered successfully. Status: Access Pending. Contact an Administrator."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/login")
def login_user(user: UserLogin):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        pw_hash = hash_password(user.password)
        cur.execute("SELECT id, username, role FROM users WHERE username = %s AND password_hash = %s", (user.username, pw_hash))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # We don't block login, but the UI/APIs will block them based on role="UNASSIGNED"
        return {"message": "Login successful", "user": {"id": row[0], "username": row[1], "role": row[2]}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
