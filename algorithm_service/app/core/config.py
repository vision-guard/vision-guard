import os

class Settings:
    USE_GPU = os.getenv("USE_GPU", "False").lower() == "true"
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    MODEL_PATH = "titan_model.pth"

settings = Settings()
