import json
from fastapi import Header, HTTPException, Depends
from app.core.database import get_db_connection

def get_current_user(user_data: str = Header(None)):
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        user = json.loads(user_data)
        
        # Verify user still exists and role in DB
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users WHERE id = %s", (user.get('id'),))
        db_user = cur.fetchone()
        cur.close()
        conn.close()

        if not db_user:
             raise HTTPException(status_code=401, detail="User not found")
        
        return {"id": db_user[0], "username": db_user[1], "role": db_user[2]}

    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_current_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    return user

def get_current_viewer_or_admin(user: dict = Depends(get_current_user)):
    role = user.get("role")
    if role not in ["ADMIN", "VIEWER"]:
        raise HTTPException(status_code=403, detail="Forbidden: Viewer or Admin role required. Unassigned users cannot access this resource.")
    return user
