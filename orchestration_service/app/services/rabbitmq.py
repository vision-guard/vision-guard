import json
import time
import logging
import threading
import collections
import pika
import cv2
import os
import numpy as np
from app.core.config import settings
from app.services.minio_service import upload_video, init_minio, delete_object
from app.core.database import init_db, get_db_connection
from app.core.vapid import get_vapid_private_key_path
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

# Per-camera Frame Buffers
FRAME_BUFFER_SIZE = 300
frame_buffers = {}  # camera_id -> deque
buffer_lock = threading.Lock()

# Cleanup interval for expired incidents (seconds)
CLEANUP_INTERVAL = 300  # 5 minutes
RETENTION_SECONDS = 3600  # 1 hour


def _get_or_create_buffer(camera_id):
    """Get or create a frame buffer for a camera."""
    if camera_id not in frame_buffers:
        frame_buffers[camera_id] = collections.deque(maxlen=FRAME_BUFFER_SIZE)
    return frame_buffers[camera_id]


def frame_consumer_loop():
    """Subscribe to all camera frames via topic exchange."""
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
            )
            channel = connection.channel()
            channel.exchange_declare(exchange='video_frames', exchange_type='topic')
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue

            # Bind with wildcard to receive frames from ALL cameras
            channel.queue_bind(
                exchange='video_frames',
                queue=queue_name,
                routing_key='frames.*'
            )

            logger.info("Listening for frames from all cameras...")

            def callback(ch, method, properties, body):
                # Extract camera_id from routing key: "frames.cam_1" -> "cam_1"
                routing_key = method.routing_key
                camera_id = routing_key.split('.', 1)[1] if '.' in routing_key else 'unknown'

                nparr = np.frombuffer(body, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    with buffer_lock:
                        buf = _get_or_create_buffer(camera_id)
                        buf.append(frame)

            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=True
            )
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Frame Consumer Error: {e}")
            time.sleep(5)


def event_consumer_loop():
    """Listen for violence detection events."""
    time.sleep(10)  # Wait for dependencies
    init_db()
    init_minio()

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
            )
            channel = connection.channel()
            channel.exchange_declare(exchange='detection_events', exchange_type='direct')
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            channel.queue_bind(
                exchange='detection_events',
                queue=queue_name,
                routing_key='violence',
            )

            logger.info("Listening for events...")

            def callback(ch, method, properties, body):
                event_data = json.loads(body)
                process_event(event_data)

            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=True
            )
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Event Consumer Error: {e}")
            time.sleep(5)


def process_event(event):
    """Process a violence detection event."""
    logger.info(f"Processing event: {event}")
    timestamp = event.get('timestamp')
    confidence = event.get('confidence')
    camera_id = event.get('camera_id', 'unknown')

    filename = save_video_clip(camera_id)
    if not filename:
        logger.error(f"[{camera_id}] Failed to save video clip locally")
        return

    object_name = f"{int(timestamp)}_{camera_id}_{os.path.basename(filename)}"
    if upload_video(object_name, filename):
        video_url = f"/minio-storage/{settings.BUCKET_NAME}/{object_name}"
        save_to_db(timestamp, confidence, camera_id, video_url)
        send_push_notifications(camera_id, confidence)
        os.remove(filename)


def send_push_notifications(camera_id, confidence):
    """Send Web Push notifications to all subscribers."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT endpoint, p256dh, auth FROM push_subscriptions")
        subscriptions = cur.fetchall()
        cur.close()
        conn.close()

        if not subscriptions:
            return

        payload = json.dumps({
            "title": "Violence Detected!",
            "body": f"Violence detected in Camera {camera_id} ({int(confidence * 100)}% confidence)",
            "url": "/suspected-videos",
            "icon": "/vite.svg",
            "badge": "/vite.svg",
        })

        vapid_private_key = get_vapid_private_key_path()
        vapid_claims = {"sub": "mailto:admin@visionguard.local"}

        for sub in subscriptions:
            endpoint, p256dh, auth = sub
            subscription_info = {
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            }
            try:
                webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=vapid_private_key,
                    vapid_claims=vapid_claims,
                )
            except WebPushException as ex:
                logger.error(f"WebPush failed for {endpoint}: {ex}")

    except Exception as e:
        logger.error(f"Error sending push notifications: {e}")


def save_video_clip(camera_id):
    """Save buffered frames for a specific camera as a WebM clip."""
    with buffer_lock:
        buf = frame_buffers.get(camera_id)
        if buf is None or len(buf) < 10:
            return None
        frames = list(buf)

    filename = f"incident_{camera_id}_{int(time.time())}.webm"
    h, w, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'VP80')
    out = cv2.VideoWriter(filename, fourcc, 30.0, (w, h))

    for f in frames:
        out.write(f)
    out.release()
    return filename


def save_to_db(timestamp, confidence, camera_id, video_url):
    """Save incident record to PostgreSQL."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO incidents (timestamp, confidence, camera_id, video_url) VALUES (%s, %s, %s, %s)",
            (timestamp, confidence, camera_id, video_url),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"DB Insert Error: {e}")


def cleanup_expired_incidents():
    """Background thread: delete incidents older than 1 hour from MinIO and PostgreSQL."""
    time.sleep(30)  # Wait for services to initialize
    logger.info("Started incident cleanup thread (retention: 1 hour)")

    while True:
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Find incidents older than 1 hour
            cur.execute(
                "SELECT id, video_url FROM incidents WHERE created_at < NOW() - INTERVAL '1 hour'"
            )
            expired = cur.fetchall()

            if expired:
                logger.info(f"Cleaning up {len(expired)} expired incident(s)...")

            for incident_id, video_url in expired:
                # Parse object name from video_url: /minio-storage/bucket/object_name
                try:
                    parts = video_url.split('/')
                    # URL format: /minio-storage/<bucket>/<object_name>
                    object_name = '/'.join(parts[3:]) if len(parts) > 3 else None
                    if object_name:
                        delete_object(object_name)
                except Exception as e:
                    logger.error(f"Failed to parse/delete MinIO object for incident {incident_id}: {e}")

                # Delete from database
                try:
                    cur.execute("DELETE FROM incidents WHERE id = %s", (incident_id,))
                except Exception as e:
                    logger.error(f"Failed to delete incident {incident_id} from DB: {e}")

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            logger.error(f"Cleanup thread error: {e}")

        time.sleep(CLEANUP_INTERVAL)


def start_consumers():
    """Start all background consumer threads."""
    t1 = threading.Thread(target=frame_consumer_loop, daemon=True)
    t2 = threading.Thread(target=event_consumer_loop, daemon=True)
    t3 = threading.Thread(target=cleanup_expired_incidents, daemon=True)
    t1.start()
    t2.start()
    t3.start()
