from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_viewer_or_admin
from app.core.config import settings

router = APIRouter()

@router.get("/stream-url")
def get_stream_url(current_user: dict = Depends(get_current_viewer_or_admin)):
    """Returns stream URLs for all cameras."""
    cameras = []
    for cam_id in settings.CAMERA_IDS:
        cameras.append({
            "camera_id": cam_id,
            "stream_url": f"{settings.CAMERA_STREAM_EXTERNAL_URL}/{cam_id}"
        })
    return {"cameras": cameras}
