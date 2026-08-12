import os

class Settings:
    CAMERA_SOURCE: str = os.getenv("CAMERA_SOURCE", "videos")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    VIDEO_FOLDER: str = os.getenv("VIDEO_FOLDER", "videos")

settings = Settings()
