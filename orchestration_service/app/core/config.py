import os

class Settings:
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "vision_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "vision_password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "vision_db")

    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minio_user")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minio_password")
    MINIO_EXTERNAL_HOST: str = os.getenv("MINIO_EXTERNAL_HOST", "visionguard.cs.colman.ac.il")
    BUCKET_NAME: str = os.getenv("BUCKET_NAME", "violent-segments")

    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    CAMERA_STREAM_EXTERNAL_URL: str = os.getenv("CAMERA_STREAM_EXTERNAL_URL", "/live")

settings = Settings()
