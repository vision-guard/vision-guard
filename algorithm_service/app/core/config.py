import os

class Settings:
    USE_GPU = os.getenv("USE_GPU", "False").lower() == "true"
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    MODEL_PATH = os.getenv("MODEL_PATH", "sentinel_best_f1.pth")
    VIOLENCE_THRESHOLD = float(os.getenv("VIOLENCE_THRESHOLD", "0.5"))
    PROB_SMOOTHING_WINDOW = int(os.getenv("PROB_SMOOTHING_WINDOW", "5"))
    CONSECUTIVE_WINDOWS_TO_ALERT = int(os.getenv("CONSECUTIVE_WINDOWS_TO_ALERT", "3"))
    ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "3"))
    CAMERA_IDS = os.getenv("CAMERA_IDS", "cam_1,cam_2,cam_3,cam_4").split(",")

settings = Settings()
