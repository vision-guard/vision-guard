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
from app.services.minio_service import upload_video, init_minio
from app.core.database import init_db, get_db_connection
from app.core.vapid import get_vapid_private_key_path
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

# Frame Buffer
FRAME_BUFFER_SIZE = 300
frame_buffer = collections.deque(maxlen=FRAME_BUFFER_SIZE)
buffer_lock = threading.Lock()

def frame_consumer_loop():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
            channel = connection.channel()
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            channel.queue_bind(exchange='video_frames', queue=queue_name)
            
            logger.info("Listening for frames...")
            
            def callback(ch, method, properties, body):
                nparr = np.frombuffer(body, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    with buffer_lock:
                        frame_buffer.append(frame)

            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Frame Consumer Error: {e}")
            time.sleep(5)

def event_consumer_loop():
    time.sleep(10) # Wait for dependencies
    init_db()
    init_minio()

    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
            channel = connection.channel()
            channel.exchange_declare(exchange='detection_events', exchange_type='direct')
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            channel.queue_bind(exchange='detection_events', queue=queue_name, routing_key='violence')
            
            logger.info("Listening for events...")

            def callback(ch, method, properties, body):
                event_data = json.loads(body)
                process_event(event_data)

            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Event Consumer Error: {e}")
            time.sleep(5)

def process_event(event):
    logger.info(f"Processing event: {event}")
    timestamp = event.get('timestamp')
    confidence = event.get('confidence')
    camera_id = event.get('camera_id')
    
    filename = save_video_clip()
    if not filename:
        logger.error("Failed to save video clip locally")
        return

    object_name = f"{int(timestamp)}_{filename}"
    if upload_video(object_name, filename):
        video_url = f"http://{settings.MINIO_EXTERNAL_HOST}/{settings.BUCKET_NAME}/{object_name}"
        save_to_db(timestamp, confidence, camera_id, video_url)
        send_push_notifications(camera_id, confidence)
        os.remove(filename)

def send_push_notifications(camera_id, confidence):
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
            "badge": "/vite.svg"
        })

        vapid_private_key = get_vapid_private_key_path()
        vapid_claims = {
            "sub": "mailto:admin@visionguard.local"
        }

        for sub in subscriptions:
            endpoint, p256dh, auth = sub
            subscription_info = {
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth}
            }
            try:
                webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=vapid_private_key,
                    vapid_claims=vapid_claims
                )
            except WebPushException as ex:
                logger.error(f"WebPush failed for {endpoint}: {ex}")

    except Exception as e:
        logger.error(f"Error sending push notifications: {e}")

def save_video_clip():
    with buffer_lock:
        if len(frame_buffer) < 10:
            return None
        frames = list(frame_buffer)
    
    filename = f"incident_{int(time.time())}.webm"
    h, w, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'VP80')
    out = cv2.VideoWriter(filename, fourcc, 30.0, (w, h))
    
    for f in frames:
        out.write(f)
    out.release()
    return filename

def save_to_db(timestamp, confidence, camera_id, video_url):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO incidents (timestamp, confidence, camera_id, video_url) VALUES (%s, %s, %s, %s)",
            (timestamp, confidence, camera_id, video_url)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"DB Insert Error: {e}")

def start_consumers():
    t1 = threading.Thread(target=frame_consumer_loop, daemon=True)
    t2 = threading.Thread(target=event_consumer_loop, daemon=True)
    t1.start()
    t2.start()
