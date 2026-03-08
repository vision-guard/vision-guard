from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_viewer_or_admin
from app.core.config import settings

router = APIRouter()

@router.get("/stream-url")
def get_stream_url(current_user: dict = Depends(get_current_viewer_or_admin)):
    """Returns the URL of the Live Video Stream for authorized clients."""
    return {"stream_url": settings.CAMERA_STREAM_EXTERNAL_URL}
