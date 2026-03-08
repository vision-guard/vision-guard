import logging
from fastapi import FastAPI
from app.api.routers import stream
from app.services.camera import start_camera_thread

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vision Guard Camera Service")

app.include_router(stream.router)

@app.on_event("startup")
def on_startup():
    logger.info("Starting Vision Guard Camera Service...")
    start_camera_thread()
