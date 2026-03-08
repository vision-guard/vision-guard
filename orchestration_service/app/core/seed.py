from app.core.database import get_db_connection
from app.core.security import hash_password
import logging

logger = logging.getLogger(__name__)

def seed_super_admin():
    """Ensures at least one ADMIN exists in the database on startup."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if an admin already exists
        cur.execute("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1")
        admin_exists = cur.fetchone()
        
        if not admin_exists:
            pw_hash = hash_password("admin123")
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'ADMIN')",
                ("admin", pw_hash)
            )
            conn.commit()
            logger.info("Database Seeded with Super Admin account (username: admin, role: ADMIN)")
        else:
            logger.info("Admin account already exists. Skipping seed.")
            
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to seed super admin: {e}")
