import json
import time
import logging
from minio import Minio
from app.core.config import settings

logger = logging.getLogger(__name__)

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False
)

def init_minio():
    try:
        if not minio_client.bucket_exists(settings.BUCKET_NAME):
            minio_client.make_bucket(settings.BUCKET_NAME)
            # Set policy to public read
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetBucketLocation", "s3:ListBucket", "s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{settings.BUCKET_NAME}", f"arn:aws:s3:::{settings.BUCKET_NAME}/*"]
                    }
                ]
            }
            minio_client.set_bucket_policy(settings.BUCKET_NAME, json.dumps(policy))
        logger.info("Minio initialized")
    except Exception as e:
        logger.error(f"Minio Error: {e}")
        time.sleep(5)
        init_minio()

def upload_video(object_name: str, file_path: str):
    try:
        minio_client.fput_object(settings.BUCKET_NAME, object_name, file_path)
        logger.info(f"Uploaded {object_name} to Minio")
        return True
    except Exception as e:
        logger.error(f"Failed to upload to Minio: {e}")
        return False
