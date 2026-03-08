import os

class Settings:
    USE_WEBCAM = os.getenv("USE_WEBCAM", "False").lower() == "true"
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    VIDEO_FOLDER = "videos"

settings = Settings()
