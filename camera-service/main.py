import logging
import threading
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from camera_mock import stream_video
from rabbitmq_client import RabbitMQClient
from config import VIDEO_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

rabbit = RabbitMQClient()
active_streams: dict[str, threading.Thread] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    rabbit.connect()
    yield
    rabbit.close()


app = FastAPI(title="Vision Guard - Camera Service (Mock)", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "active_streams": list(active_streams.keys())}


@app.get("/videos")
def list_videos():
    """List available video files that can be streamed."""
    video_dir = Path(VIDEO_DIR)
    if not video_dir.exists():
        return {"videos": []}
    extensions = {".mp4", ".avi", ".mov", ".mkv"}
    files = [f.name for f in video_dir.iterdir() if f.suffix.lower() in extensions]
    return {"videos": files}


@app.post("/stream/{camera_id}")
def start_stream(camera_id: str, filename: str):
    """Start streaming a video file as a mock camera feed.

    Args:
        camera_id: Identifier for this camera source.
        filename: Name of the video file inside the videos directory.
    """
    if camera_id in active_streams and active_streams[camera_id].is_alive():
        raise HTTPException(status_code=409, detail=f"Camera {camera_id} is already streaming")

    video_path = Path(VIDEO_DIR) / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {filename}")

    thread = threading.Thread(
        target=stream_video,
        args=(str(video_path), camera_id, rabbit),
        daemon=True,
    )
    thread.start()
    active_streams[camera_id] = thread

    return {"message": f"Started streaming {filename} as camera {camera_id}"}


@app.post("/stop/{camera_id}")
def stop_stream(camera_id: str):
    """Stop info for a camera stream (stream finishes when video ends)."""
    if camera_id not in active_streams:
        raise HTTPException(status_code=404, detail=f"No active stream for camera {camera_id}")
    del active_streams[camera_id]
    return {"message": f"Removed camera {camera_id} from active streams"}
