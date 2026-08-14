import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from app.services.camera import get_latest_frame, get_all_camera_ids

router = APIRouter()


@router.get("/health")
async def health_check():
    """Returns aggregated health status across all cameras."""
    camera_ids = get_all_camera_ids()
    statuses = {}
    all_ready = True
    for cam_id in camera_ids:
        frame = get_latest_frame(cam_id)
        ready = frame is not None
        statuses[cam_id] = ready
        if not ready:
            all_ready = False

    if all_ready:
        return JSONResponse({"status": "ok", "streaming": True, "cameras": statuses})
    elif any(statuses.values()):
        return JSONResponse({"status": "partial", "streaming": True, "cameras": statuses})
    return JSONResponse({"status": "starting", "streaming": False, "cameras": statuses}, status_code=503)


@router.get("/health/{camera_id}")
async def camera_health_check(camera_id: str):
    """Returns health status for a specific camera."""
    if camera_id not in get_all_camera_ids():
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    frame = get_latest_frame(camera_id)
    if frame:
        return JSONResponse({"status": "ok", "streaming": True, "camera_id": camera_id})
    return JSONResponse({"status": "starting", "streaming": False, "camera_id": camera_id}, status_code=503)


@router.get("/cameras")
async def list_cameras():
    """Returns a list of all available camera IDs."""
    return JSONResponse({"cameras": get_all_camera_ids()})


@router.get("/live/{camera_id}")
async def video_feed(camera_id: str):
    """MJPEG stream for a specific camera."""
    if camera_id not in get_all_camera_ids():
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    def generate():
        # Wait until at least one frame is available before starting the stream
        wait_start = time.time()
        while time.time() - wait_start < 30:
            frame = get_latest_frame(camera_id)
            if frame:
                break
            time.sleep(0.5)

        while True:
            frame = get_latest_frame(camera_id)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1 / 30)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
