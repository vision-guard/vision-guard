import cv2
import time
import glob
import logging
import threading
import pika
from app.core.config import settings

logger = logging.getLogger(__name__)

latest_frame = None
lock = threading.Lock()

def get_video_source():
    if settings.USE_WEBCAM:
        logger.info("Using Webcam as video source")
        return cv2.VideoCapture(0)
    else:
        logger.info(f"Using Video Files from {settings.VIDEO_FOLDER} as source")
        files = sorted(glob.glob(f"{settings.VIDEO_FOLDER}/*.mp4") + glob.glob(f"{settings.VIDEO_FOLDER}/*.avi"))
        if not files:
            logger.warning("No video files found! streaming will be black.")
            return None
        return files

def get_rabbitmq_connection():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
            channel = connection.channel()
            channel.exchange_declare(exchange='video_frames', exchange_type='fanout')
            logger.info("Connected to RabbitMQ")
            return connection, channel
        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ unavailable, retrying in 5s...")
            time.sleep(5)

def video_capture_loop():
    global latest_frame
    
    connection, channel = get_rabbitmq_connection()
    video_source = get_video_source()
    cap = None
    file_index = 0

    while True:
        fps = 30.0 
        if settings.USE_WEBCAM:
            if cap is None or not cap.isOpened():
                try:
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        raise Exception("cap.isOpened() returned False. Device may be busy or unavailable.")
                except Exception as e:
                    logger.warning(f"Failed to access webcam: {e}. Gracefully falling back to video files.")
                    settings.USE_WEBCAM = False
                    video_source = sorted(glob.glob(f"{settings.VIDEO_FOLDER}/*.mp4") + glob.glob(f"{settings.VIDEO_FOLDER}/*.avi"))
                    continue
        else:
            if not video_source:
                 video_source = sorted(glob.glob(f"{settings.VIDEO_FOLDER}/*.mp4") + glob.glob(f"{settings.VIDEO_FOLDER}/*.avi"))
                 if not video_source:
                     time.sleep(1)
                     continue
            
            if cap is None or not cap.isOpened():
                current_file = video_source[file_index]
                logger.info(f"Playing {current_file}")
                cap = cv2.VideoCapture(current_file)
        
        if cap is not None and cap.isOpened():
            detected_fps = cap.get(cv2.CAP_PROP_FPS)
            if detected_fps > 0 and detected_fps < 120:
                fps = detected_fps
        
        start_time = time.time()
        ret, frame = cap.read()
        
        if not ret:
            if not settings.USE_WEBCAM and video_source:
                cap.release()
                file_index = (file_index + 1) % len(video_source)
                continue
            else:
                cap.release()
                time.sleep(1)
                continue
        
        frame = cv2.resize(frame, (640, 360))
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        frame_bytes = buffer.tobytes()
        
        with lock:
            latest_frame = frame_bytes

        try:
             channel.basic_publish(exchange='video_frames', routing_key='', body=frame_bytes)
        except Exception as e:
            logger.error(f"Failed to publish to RabbitMQ: {e}")
            connection, channel = get_rabbitmq_connection() 

        processing_time = time.time() - start_time
        time.sleep(max(0, 1/fps - processing_time))

def start_camera_thread():
    thread = threading.Thread(target=video_capture_loop, daemon=True)
    thread.start()

def get_latest_frame():
    with lock:
        return latest_frame
