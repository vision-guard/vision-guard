from fastapi import APIRouter, HTTPException, Depends
from app.api.dependencies import get_current_viewer_or_admin
from app.core.database import get_db_connection
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Note: In standard REST, this might be `/incidents`, mapping to `/suspected_videos` in frontend config
@router.get("/")
def get_suspected_videos(current_user: dict = Depends(get_current_viewer_or_admin)):
    """Viewers and Admins can see the incidents."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, timestamp, confidence, camera_id, video_url, created_at FROM incidents ORDER BY created_at DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        incidents = []
        for row in rows:
            incidents.append({
                "id": row[0],
                "timestamp": row[1],
                "confidence": row[2],
                "camera_id": row[3],
                "video_url": row[4],
                "created_at": str(row[5])
            })
        return incidents
    except Exception as e:
        logger.error(f"API Error: {e}")
        return []
