import cv2
import time
import logging
import threading
import pika
from app.core.config import settings

logger = logging.getLogger(__name__)

latest_frames = {}   # camera_id -> (frame_bytes, timestamp)
lock = threading.Lock()


def get_rabbitmq_connection():
    """Connect to RabbitMQ and declare the topic exchange."""
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
            )
            channel = connection.channel()
            channel.exchange_declare(exchange='video_frames', exchange_type='topic')
            logger.info("Connected to RabbitMQ")
            return connection, channel
        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ unavailable, retrying in 5s...")
            time.sleep(5)


def camera_loop(camera_id, video_file):
    """Capture loop for a single camera. Runs in its own thread."""
    global latest_frames

    video_path = f"{settings.VIDEO_FOLDER}/{video_file}"
    routing_key = f"frames.{camera_id}"
    connection, channel = get_rabbitmq_connection()
    cap = None

    logger.info(f"[{camera_id}] Starting camera loop with {video_path}")

    while True:
        # Open or re-open the video file
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"[{camera_id}] Failed to open {video_path}, retrying in 2s...")
                time.sleep(2)
                continue
            logger.info(f"[{camera_id}] Playing {video_path}")

        # Detect FPS
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps >= 120:
            fps = 30.0

        start_time = time.time()
        ret, frame = cap.read()

        if not ret:
            # Video ended — loop back to beginning seamlessly
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # Resize and encode
        frame = cv2.resize(frame, (640, 360))
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        frame_bytes = buffer.tobytes()

        # Store latest frame with timestamp
        with lock:
            latest_frames[camera_id] = (frame_bytes, time.time())

        # Publish to RabbitMQ
        try:
            channel.basic_publish(
                exchange='video_frames',
                routing_key=routing_key,
                body=frame_bytes
            )
        except Exception as e:
            logger.error(f"[{camera_id}] Failed to publish to RabbitMQ: {e}")
            try:
                connection.close()
            except Exception:
                pass
            connection, channel = get_rabbitmq_connection()

        # Pace at video FPS
        processing_time = time.time() - start_time
        time.sleep(max(0, 1 / fps - processing_time))


def start_camera_threads():
    """Spawn a capture thread for each configured camera."""
    for camera_id, video_file in settings.CAMERAS.items():
        thread = threading.Thread(
            target=camera_loop,
            args=(camera_id, video_file),
            daemon=True,
            name=f"camera-{camera_id}"
        )
        thread.start()
        logger.info(f"Started thread for {camera_id} -> {video_file}")


def get_latest_frame(camera_id, max_age=5.0):
    """Get the latest JPEG frame for a specific camera.

    Returns the frame bytes only if it was produced within *max_age* seconds.
    Otherwise returns None so callers know the feed is stale.
    """
    with lock:
        entry = latest_frames.get(camera_id)
        if entry is None:
            return None
        frame_bytes, ts = entry
        if time.time() - ts > max_age:
            return None
        return frame_bytes


def get_all_camera_ids():
    """Return list of all configured camera IDs."""
    return list(settings.CAMERAS.keys())
