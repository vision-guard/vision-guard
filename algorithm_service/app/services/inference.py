import os
import time
import json
import logging
import torch
import cv2
import pika
import numpy as np
import collections
from app.core.config import settings
from app.models.architectures import UltimateGladiator

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)

# Constants
SEQ_LENGTH = 16
FRAME_SKIP = 2

# Check device
device = 'cpu'
if settings.USE_GPU:
    if torch.cuda.is_available():
        device = 'cuda'
        logger.info("Using GPU for inference")
    else:
        logger.warning("USE_GPU is True but CUDA is not available. Using CPU.")
else:
    logger.info("Using CPU for inference")

# Load Model (תיקון 2: בלי num_classes=2, קוראים למודל בדיוק כמו באימון)
model = UltimateGladiator()
model.to(device)
model.eval()

if os.path.exists(settings.MODEL_PATH):
    logger.info(f"Loading weights from {settings.MODEL_PATH}")
    try:
        state_dict = torch.load(settings.MODEL_PATH, map_location=device)
        model.load_state_dict(state_dict, strict=False)
    except Exception as e:
        logger.error(f"Failed to load model weights: {e}")
else:
    logger.warning(f"Model file {settings.MODEL_PATH} not found! Using random initialization.")

# זיכרון גלובלי של המערכת (לא נמחק אף פעם!)
sliding_window = collections.deque(maxlen=SEQ_LENGTH)
prob_buffer = collections.deque(maxlen=5) # בולם זעזועים (ממוצע נע)
frame_counter = 0

def process_single_frame(frame):
    global frame_counter
    
    frame_counter += 1
    if frame_counter % FRAME_SKIP != 0:
        return
        
    # 1. הכנת הפריים (המרת צבעים ונרמול כמו באימון)
    f = cv2.resize(frame, (112, 112))
    f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB) # המודל אומן על RGB
    curr_frame = f.astype(np.float32) / 255.0
    
    # הוספה לחלון הזז של הפריים הרגיל (RGB)
    sliding_window.append(curr_frame)
    
    # 3. מריצים זיהוי רק כשיש 16 פריימים מוכנים
    if len(sliding_window) == SEQ_LENGTH:
        # בניה מחדש של הוידאו בדיוק כמו ב-train_titan.py (frame 0 motion diff is 0)
        raw_frames = list(sliding_window)
        combined_frames = []
        for i in range(len(raw_frames)):
            c_frame = raw_frames[i]
            p_frame = c_frame if i == 0 else raw_frames[i-1]
            m_diff = np.abs(c_frame - p_frame)
            combined_frames.append(np.concatenate([c_frame, m_diff], axis=-1))
            
        input_tensor = torch.tensor(np.array(combined_frames), dtype=torch.float32).permute(3, 0, 1, 2)
        input_tensor = input_tensor.unsqueeze(0).to(device)
        
        with torch.no_grad():
            output = model(input_tensor)
            # שימוש ב-Sigmoid כמו באימון
            raw_prob = torch.sigmoid(output).item()
            
        # 4. ממוצע נע למניעת קפיצות רגעיות
        prob_buffer.append(raw_prob)
        smoothed_prob = sum(prob_buffer) / len(prob_buffer)
        
        logger.info(f"Inference result: Raw={raw_prob:.4f} Smoothed={smoothed_prob:.4f}")
        
        # 5. שיגור התראה ל-RabbitMQ אם חצינו את הרף
        if smoothed_prob > 0.478:
            logger.info("🚨 PUBLISH: Violence Threshold Crossed!")
            publish_event(smoothed_prob)

def publish_event(confidence):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
        channel = connection.channel()
        channel.exchange_declare(exchange='detection_events', exchange_type='direct')
        
        event = {
            "timestamp": time.time(),
            "confidence": confidence,
            "camera_id": "cam_1", 
            "type": "violence"
        }
        
        channel.basic_publish(exchange='detection_events', routing_key='violence', body=json.dumps(event))
        logger.info(f"Published violence event: {event}")
        connection.close()
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")

def start_consumer_loop():
    # איפוס נתונים במקרה של הפעלה מחדש
    sliding_window.clear()
    prob_buffer.clear()
    global frame_counter
    frame_counter = 0

    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
            channel = connection.channel()
            
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            channel.exchange_declare(exchange='video_frames', exchange_type='fanout')
            channel.queue_bind(exchange='video_frames', queue=queue_name)
            
            logger.info("Waiting for video frames from RabbitMQ...")

            def callback(ch, method, properties, body):
                nparr = np.frombuffer(body, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    process_single_frame(frame)

            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ unavailable, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(1)