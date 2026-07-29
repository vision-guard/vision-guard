import os

class Settings:
    USE_GPU = os.getenv("USE_GPU", "False").lower() == "true"
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    MODEL_PATH = "sentinel_best_f1.pth"

settings = Settings()
