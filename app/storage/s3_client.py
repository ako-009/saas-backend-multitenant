import boto3
from app.core.config import settings


def get_s3_client():
    """
    Returns a boto3 S3 client.
    
    In development: points to LocalStack (localhost:4566)
    In production: points to real AWS S3
    
    The only difference is the endpoint_url parameter.
    All other code — generating pre-signed URLs, uploading,
    listing — is identical. This is the power of boto3's
    abstraction.
    
    INTERVIEW POINT:
    "We used boto3 with a configurable endpoint URL so the same
    code works against LocalStack in development and real AWS
    in production. No code changes needed — just swap the
    environment variable."
    """
    kwargs = {
        "region_name": settings.aws_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
    }

    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url

    return boto3.client("s3", **kwargs)


s3_client = get_s3_client()


def create_bucket_if_not_exists():
    """
    Creates the S3 bucket if it doesn't exist.
    Called on app startup.
    Safe to call multiple times.
    """
    try:
        s3_client.head_bucket(Bucket=settings.s3_bucket_name)
    except Exception:
        if settings.aws_region == "us-east-1":
            s3_client.create_bucket(Bucket=settings.s3_bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=settings.s3_bucket_name,
                CreateBucketConfiguration={
                    "LocationConstraint": settings.aws_region
                }
            )
        print(f"✅ S3 bucket '{settings.s3_bucket_name}' created")