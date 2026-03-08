import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import auth, users, incidents, config
from app.services.rabbitmq import start_consumers
from app.core.seed import seed_super_admin
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vision Guard Orchestration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routers import auth, users, incidents, config, push

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# Note: For frontend compatibility we keep /suspected_videos instead of /api/incidents
# Unless we refactor the frontend calls simultaneously. We'll map the UI route specifically.
app.include_router(incidents.router, prefix="/suspected_videos", tags=["incidents"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(push.router, prefix="/api/push", tags=["push"])

def startup_tasks():
    # Wait lightly for db/mq to be truly ready in docker network
    time.sleep(15)
    seed_super_admin()
    start_consumers()

@app.on_event("startup")
def on_startup():
    logger.info("Starting Vision Guard Orchestration Service...")
    # Seed and Consumers need to wait for DB and RabbitMQ connections
    # We use a background thread so FastAPI boots up and serves Readiness probes immediately
    t = threading.Thread(target=startup_tasks, daemon=True)
    t.start()
