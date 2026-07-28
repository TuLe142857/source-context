import boto3

from mypy_boto3_s3 import S3Client
from .config import settings
from functools import lru_cache


@lru_cache
def get_s3_client() -> S3Client:
    """
    Get an S3 client.
    Returns:

    """
    s3_client = boto3.client(
        service_name="s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY.get_secret_value(),
    )
    return s3_client


def create_default_bucket_if_not_exists(s3_client: S3Client) -> None:
    try:
        s3_client.create_bucket(Bucket=settings.S3_DEFAULT_BUCKET)
    except s3_client.exceptions.BucketAlreadyExists:
        return
