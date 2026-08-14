import os

class Settings:
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "vision_user")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "vision_password")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "vision_db")
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_user")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_password")
    MINIO_EXTERNAL_HOST = os.getenv("MINIO_EXTERNAL_HOST", "localhost:9000")
    CAMERA_STREAM_EXTERNAL_URL = os.getenv("CAMERA_STREAM_EXTERNAL_URL", "http://localhost:8000/live")
    BUCKET_NAME = "violent-segments"
    CAMERA_IDS = os.getenv("CAMERA_IDS", "cam_1,cam_2,cam_3,cam_4").split(",")

settings = Settings()
