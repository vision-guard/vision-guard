import os
import time
import json
import logging
import torch
import cv2
import pika
import numpy as np
from app.core.config import settings
from app.models.architectures import UltimateGladiator

logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 16

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

# Load Model
model = UltimateGladiator(num_classes=2)
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

def process_buffer(frames):
    """
    Process a batch of frames and run inference.
    """
    if len(frames) < BATCH_SIZE:
        return

    processed_frames = []
    for f in frames:
        f = cv2.resize(f, (112, 112))
        f = f.astype(np.float32) / 255.0
        f = (f - 0.5) / 0.5
        processed_frames.append(f)
    
    input_tensor = torch.tensor(np.array(processed_frames)).permute(3, 0, 1, 2)
    input_tensor = input_tensor.unsqueeze(0)
    input_tensor = input_tensor.to(device)
    
    with torch.no_grad():
        output = model(input_tensor)
        probs = torch.softmax(output, dim=1)
        violence_prob = probs[0][1].item()
        
        logger.info(f"Inference result: Violence Prob: {violence_prob:.4f}")
        
        if violence_prob > 0.478:
            logger.info(f"PUBLISH")
            publish_event(violence_prob)

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
    frame_buffer = []
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
            channel = connection.channel()
            
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            channel.exchange_declare(exchange='video_frames', exchange_type='fanout')
            channel.queue_bind(exchange='video_frames', queue=queue_name)
            
            logger.info("Waiting for video frames...")

            def callback(ch, method, properties, body):
                nparr = np.frombuffer(body, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    return

                frame_buffer.append(frame)
                
                if len(frame_buffer) >= BATCH_SIZE:
                    process_buffer(frame_buffer)
                    frame_buffer.clear() 

            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ unavailable, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(1)
