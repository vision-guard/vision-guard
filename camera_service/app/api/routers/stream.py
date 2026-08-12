import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from app.services.camera import get_latest_frame

router = APIRouter()

@router.get("/health")
async def health_check():
    """Returns whether the camera service has frames available."""
    frame = get_latest_frame()
    if frame:
        return JSONResponse({"status": "ok", "streaming": True})
    return JSONResponse({"status": "starting", "streaming": False}, status_code=503)

@router.get("/live")
async def video_feed():
    def generate():
        # Wait until at least one frame is available before starting the stream
        # This prevents the browser from receiving an empty response and firing onError
        wait_start = time.time()
        while time.time() - wait_start < 30:  # wait up to 30s for first frame
            frame = get_latest_frame()
            if frame:
                break
            time.sleep(0.5)

        while True:
            frame = get_latest_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1/30)

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")
