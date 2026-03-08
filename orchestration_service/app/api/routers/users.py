from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models.schemas import UserAdd, UserUpdateRole
from app.api.dependencies import get_current_admin
from app.core.database import get_db_connection
from app.core.security import hash_password
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
def list_users(current_user: dict = Depends(get_current_admin)):
    """Only Admins can list all users."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, phone, role, created_at FROM users ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        users = []
        for row in rows:
             users.append({
                 "id": row[0],
                 "username": row[1],
                 "email": row[2],
                 "phone": row[3],
                 "role": row[4],
                 "created_at": str(row[5])
             })
        return users
    except Exception as e:
        logger.error(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/add")
def add_user(user: UserAdd, current_user: dict = Depends(get_current_admin)):
    """Only Admins can directly add new users with default passwords."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")
        
        pw_hash = hash_password("123456") # Default password for added users
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'UNASSIGNED')",
            (user.username, pw_hash)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"message": f"User {user.username} added successfully with default password '123456' and role 'UNASSIGNED'."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{user_id}/role")
def update_user_role(user_id: int, role_data: UserUpdateRole, current_user: dict = Depends(get_current_admin)):
    """Only Admins can update roles."""
    valid_roles = ["ADMIN", "VIEWER", "UNASSIGNED"]
    if role_data.role not in valid_roles:
         raise HTTPException(status_code=400, detail="Invalid role specified.")
         
    try:
         conn = get_db_connection()
         cur = conn.cursor()
         cur.execute("UPDATE users SET role = %s WHERE id = %s RETURNING id", (role_data.role, user_id))
         updated_id = cur.fetchone()
         conn.commit()
         cur.close()
         conn.close()
         
         if not updated_id:
              raise HTTPException(status_code=404, detail="User not found")
         return {"message": f"User role successfully updated to {role_data.role}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB Update Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
