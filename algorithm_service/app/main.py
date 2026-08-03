import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)

from app.services.inference import start_consumer_loop

def main():
    logger.info("Starting Vision Guard Algorithm Service...")
    start_consumer_loop()

if __name__ == "__main__":
    main()
