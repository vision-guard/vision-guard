import json
import time
import logging
from minio import Minio
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
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
                        "Resource": [
                            f"arn:aws:s3:::{settings.BUCKET_NAME}",
                            f"arn:aws:s3:::{settings.BUCKET_NAME}/*",
                        ],
                    }
                ],
            }
            minio_client.set_bucket_policy(settings.BUCKET_NAME, json.dumps(policy))

        # Set lifecycle policy — safety net: auto-expire objects after 1 day
        set_lifecycle_policy()
        logger.info("Minio initialized with lifecycle policy")
    except Exception as e:
        logger.error(f"Minio Error: {e}")
        time.sleep(5)
        init_minio()


def set_lifecycle_policy():
    """Set bucket lifecycle to auto-delete objects after 1 day (safety net).
    Exact 1-hour retention is handled by the cleanup_expired_incidents thread."""
    try:
        rule = Rule(
            "auto-expire-1d",
            status="Enabled",
            expiration=Expiration(days=1),
        )
        config = LifecycleConfig([rule])
        minio_client.set_bucket_lifecycle(settings.BUCKET_NAME, config)
        logger.info("MinIO lifecycle policy set: auto-expire after 1 day")
    except Exception as e:
        logger.warning(f"Failed to set lifecycle policy (non-fatal): {e}")


def upload_video(object_name: str, file_path: str):
    try:
        minio_client.fput_object(settings.BUCKET_NAME, object_name, file_path)
        logger.info(f"Uploaded {object_name} to Minio")
        return True
    except Exception as e:
        logger.error(f"Failed to upload to Minio: {e}")
        return False


def delete_object(object_name: str):
    """Delete a single object from MinIO."""
    try:
        minio_client.remove_object(settings.BUCKET_NAME, object_name)
        logger.info(f"Deleted {object_name} from Minio")
        return True
    except Exception as e:
        logger.error(f"Failed to delete {object_name} from Minio: {e}")
        return False
