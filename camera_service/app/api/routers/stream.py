import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.camera import get_latest_frame

router = APIRouter()

@router.get("/live")
async def video_feed():
    def generate():
        while True:
            frame = get_latest_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1/30)

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")
