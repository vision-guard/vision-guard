import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "video_frames")
VIDEO_DIR = os.getenv("VIDEO_DIR", "./videos")

# Frame sampling rate (frames per second sent to the algorithm)
FPS = int(os.getenv("FPS", 4))

# Number of frames per clip sent to the model for one prediction
CLIP_LENGTH = int(os.getenv("CLIP_LENGTH", 16))

# Seconds of video to skip between clips
CLIP_GAP = float(os.getenv("CLIP_GAP", 2.0))
