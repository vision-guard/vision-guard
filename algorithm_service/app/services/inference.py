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
from app.models.architectures import StreamSentinelViT

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

# Load model architecture — shared across all camera pipelines
model = StreamSentinelViT()
model.to(device)

if not os.path.exists(settings.MODEL_PATH):
    raise FileNotFoundError(f"Model file {settings.MODEL_PATH} not found")

logger.info(f"Loading weights from {settings.MODEL_PATH}")
try:
    checkpoint = torch.load(settings.MODEL_PATH, map_location=device)
    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        state_dict = checkpoint["state_dict"]
    else:
        state_dict = checkpoint

    model.load_state_dict(state_dict, strict=True)
    model.eval()
    logger.info(
        "Model loaded successfully | threshold=%.3f smoothing=%d consecutive=%d cooldown=%.1fs",
        settings.VIOLENCE_THRESHOLD,
        settings.PROB_SMOOTHING_WINDOW,
        settings.CONSECUTIVE_WINDOWS_TO_ALERT,
        settings.ALERT_COOLDOWN_SECONDS,
    )
except Exception as e:
    raise RuntimeError(f"Failed to load model weights from {settings.MODEL_PATH}: {e}") from e


class CameraState:
    """Isolated inference state for a single camera stream."""

    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.sliding_window = collections.deque(maxlen=SEQ_LENGTH)
        self.prob_buffer = collections.deque(maxlen=settings.PROB_SMOOTHING_WINDOW)
        self.frame_counter = 0
        self.above_threshold_streak = 0
        self.last_alert_ts = 0.0

    def reset(self):
        self.sliding_window.clear()
        self.prob_buffer.clear()
        self.frame_counter = 0
        self.above_threshold_streak = 0
        self.last_alert_ts = 0.0


# Per-camera state instances
camera_states = {cam_id: CameraState(cam_id) for cam_id in settings.CAMERA_IDS}


def process_single_frame(camera_id, frame):
    """Process a single frame for a specific camera."""
    state = camera_states.get(camera_id)
    if state is None:
        # Dynamically create state for unknown cameras
        state = CameraState(camera_id)
        camera_states[camera_id] = state

    state.frame_counter += 1
    if state.frame_counter % FRAME_SKIP != 0:
        return

    # 1. Prepare frame (color conversion and normalization)
    f = cv2.resize(frame, (112, 112))
    f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)  # Model trained on RGB
    curr_frame = f.astype(np.float32) / 255.0

    # Add to sliding window
    state.sliding_window.append(curr_frame)

    # 3. Run inference only when 16 frames are ready
    if len(state.sliding_window) == SEQ_LENGTH:
        # Reconstruct motion diff (frame 0 motion diff is 0)
        raw_frames = list(state.sliding_window)
        combined_frames = []
        for i in range(len(raw_frames)):
            c_frame = raw_frames[i]
            p_frame = c_frame if i == 0 else raw_frames[i - 1]
            m_diff = np.abs(c_frame - p_frame)
            combined_frames.append(np.concatenate([c_frame, m_diff], axis=-1))

        input_tensor = torch.tensor(
            np.array(combined_frames), dtype=torch.float32
        ).permute(3, 0, 1, 2)
        input_tensor = input_tensor.unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(input_tensor)
            raw_prob = torch.sigmoid(output).item()

        # Smooth prediction to reduce short spikes.
        state.prob_buffer.append(raw_prob)
        smoothed_prob = sum(state.prob_buffer) / len(state.prob_buffer)

        logger.info(
            f"[{camera_id}] Inference result: Raw={raw_prob:.4f} Smoothed={smoothed_prob:.4f}"
        )

        if smoothed_prob >= settings.VIOLENCE_THRESHOLD:
            state.above_threshold_streak += 1
        else:
            state.above_threshold_streak = 0

        # Debounce: require consecutive high windows and cooldown gap between alerts.
        now_ts = time.time()
        can_publish = (now_ts - state.last_alert_ts) >= settings.ALERT_COOLDOWN_SECONDS
        if (
            state.above_threshold_streak >= settings.CONSECUTIVE_WINDOWS_TO_ALERT
            and can_publish
        ):
            logger.info(f"🚨 [{camera_id}] PUBLISH: Violence Threshold Crossed!")
            publish_event(smoothed_prob, camera_id)
            state.last_alert_ts = now_ts


def publish_event(confidence, camera_id):
    """Publish a violence detection event for a specific camera."""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
        )
        channel = connection.channel()
        channel.exchange_declare(exchange='detection_events', exchange_type='direct')

        event = {
            "timestamp": time.time(),
            "confidence": confidence,
            "camera_id": camera_id,
            "type": "violence",
        }

        channel.basic_publish(
            exchange='detection_events',
            routing_key='violence',
            body=json.dumps(event),
        )
        logger.info(f"[{camera_id}] Published violence event: {event}")
        connection.close()
    except Exception as e:
        logger.error(f"[{camera_id}] Failed to publish event: {e}")


def start_consumer_loop():
    """Subscribe to all camera frames via topic exchange and process them."""
    # Reset all camera states
    for state in camera_states.values():
        state.reset()

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
            )
            channel = connection.channel()

            # Declare topic exchange (must match camera service)
            channel.exchange_declare(exchange='video_frames', exchange_type='topic')

            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue

            # Bind with wildcard to receive frames from ALL cameras
            channel.queue_bind(
                exchange='video_frames',
                queue=queue_name,
                routing_key='frames.*'
            )

            logger.info(
                f"Waiting for video frames from {len(camera_states)} cameras via RabbitMQ..."
            )

            def callback(ch, method, properties, body):
                # Extract camera_id from routing key: "frames.cam_1" -> "cam_1"
                routing_key = method.routing_key
                camera_id = routing_key.split('.', 1)[1] if '.' in routing_key else 'unknown'

                nparr = np.frombuffer(body, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is not None:
                    process_single_frame(camera_id, frame)

            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=True
            )
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ unavailable, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(1)