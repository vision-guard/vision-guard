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
stream_thread: threading.Thread | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    rabbit.connect()
    yield
    rabbit.close()


app = FastAPI(title="Vision Guard - Camera Service (Mock)", lifespan=lifespan)


@app.get("/health")
def health():
    is_streaming = stream_thread is not None and stream_thread.is_alive()
    return {"status": "ok", "streaming": is_streaming}


@app.get("/videos")
def list_videos():
    """List available video files that can be streamed."""
    video_dir = Path(VIDEO_DIR)
    if not video_dir.exists():
        return {"videos": []}
    extensions = {".mp4", ".avi", ".mov", ".mkv"}
    files = [f.name for f in video_dir.iterdir() if f.suffix.lower() in extensions]
    return {"videos": files}


@app.post("/stream")
def start_stream(filename: str):
    """Start streaming a video file as a mock camera feed."""
    global stream_thread

    if stream_thread is not None and stream_thread.is_alive():
        raise HTTPException(status_code=409, detail="A stream is already running")

    video_path = Path(VIDEO_DIR) / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {filename}")

    stream_thread = threading.Thread(
        target=stream_video,
        args=(str(video_path), rabbit),
        daemon=True,
    )
    stream_thread.start()

    return {"message": f"Started streaming {filename}"}


@app.post("/stop")
def stop_stream():
    """Clear the stream reference (stream finishes when video ends)."""
    global stream_thread
    if stream_thread is None or not stream_thread.is_alive():
        raise HTTPException(status_code=404, detail="No active stream")
    stream_thread = None
    return {"message": "Stream removed"}
