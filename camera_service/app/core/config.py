import os

class Settings:
    USE_WEBCAM = os.getenv("USE_WEBCAM", "False").lower() == "true"
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    VIDEO_FOLDER = "videos"

    # Multi-camera configuration: camera_id -> video file
    CAMERAS = {
        "cam_1": "t_v001_converted.avi",   # Violent
        "cam_2": "t_n001_converted.avi",    # Normal
        "cam_3": "t_n002_converted.avi",    # Normal
        "cam_4": "t_n001_converted.avi",    # Normal (reuse)
    }

settings = Settings()
