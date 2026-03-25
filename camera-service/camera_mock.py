import cv2
import time
import uuid
import logging
from datetime import datetime, timezone

from config import VIDEO_DIR, FPS, CLIP_LENGTH, CLIP_GAP
from rabbitmq_client import RabbitMQClient

logger = logging.getLogger(__name__)


def stream_video(video_path: str, camera_id: str, rabbit: RabbitMQClient):
    """Read a video file and publish frame clips to RabbitMQ.

    Strategy (sliding window):
      - Collect CLIP_LENGTH frames at the target FPS  (e.g. 16 frames = ~4 sec at 4 FPS)
      - Skip CLIP_GAP seconds of video
      - Repeat

    Each clip gets a unique clip_id so the Algorithm Service knows
    which frames belong together for a single prediction.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return

    original_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    # How many raw frames to skip between each sampled frame
    sample_interval = max(1, int(original_fps / FPS))
    # How many raw frames to skip during the gap between clips
    gap_frames = int(original_fps * CLIP_GAP)

    frame_count = 0
    total_sent = 0
    clip_number = 0

    logger.info(
        f"Streaming {video_path} (camera={camera_id}, "
        f"{FPS} fps, clip={CLIP_LENGTH} frames, gap={CLIP_GAP}s)"
    )

    while cap.isOpened():
        clip_id = f"{camera_id}_{uuid.uuid4().hex[:8]}"
        clip_frame_index = 0
        clip_number += 1

        # --- Phase 1: Collect one clip ---
        while clip_frame_index < CLIP_LENGTH:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                logger.info(f"Finished {video_path}: sent {total_sent} frames in {clip_number} clips")
                return

            frame_count += 1

            if frame_count % sample_interval != 0:
                continue

            _, buffer = cv2.imencode(".jpg", frame)

            headers = {
                "camera_id": camera_id,
                "clip_id": clip_id,
                "clip_frame_index": clip_frame_index,
                "clip_length": CLIP_LENGTH,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "frame_number": frame_count,
            }

            rabbit.publish(body=buffer.tobytes(), headers=headers)
            clip_frame_index += 1
            total_sent += 1
            time.sleep(1.0 / FPS)

        logger.info(f"Clip {clip_number} sent ({clip_id}), skipping {CLIP_GAP}s gap")

        # --- Phase 2: Skip the gap ---
        skipped = 0
        while skipped < gap_frames:
            ret, _ = cap.read()
            if not ret:
                cap.release()
                logger.info(f"Finished {video_path}: sent {total_sent} frames in {clip_number} clips")
                return
            skipped += 1

    cap.release()
