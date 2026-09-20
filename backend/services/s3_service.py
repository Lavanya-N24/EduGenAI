"""
EduGenAI - Amazon S3 Cloud Storage Service
Handles automatic upload and global streaming of generated video lessons and media assets.
Includes zero-downtime fallback to local storage if AWS keys are not configured.
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    AWS_S3_BUCKET_NAME,
    AWS_CLOUDFRONT_DOMAIN,
)

logger = logging.getLogger("EduGenAI.S3")

_s3_client = None


def is_s3_configured() -> bool:
    """Check if AWS S3 credentials are provided."""
    return bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_BUCKET_NAME)


def _get_s3_client():
    """Lazy initialize boto3 S3 client."""
    global _s3_client
    if _s3_client is None and is_s3_configured():
        import boto3
        from botocore.config import Config

        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )
    return _s3_client


def _sync_upload(local_path: Path, s3_key: str, content_type: str) -> str:
    """Synchronous upload called via asyncio.to_thread."""
    client = _get_s3_client()
    extra_args = {"ContentType": content_type}

    logger.info(f"📤 Uploading {local_path.name} to S3 bucket '{AWS_S3_BUCKET_NAME}'...")
    client.upload_file(str(local_path), AWS_S3_BUCKET_NAME, s3_key, ExtraArgs=extra_args)

    # Return CloudFront or standard S3 public URL
    if AWS_CLOUDFRONT_DOMAIN:
        domain = AWS_CLOUDFRONT_DOMAIN.rstrip("/")
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        url = f"{domain}/{s3_key}"
    else:
        url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

    logger.info(f"✅ S3 Upload complete: {url}")
    return url


async def upload_file_to_s3(
    local_path: Path,
    s3_key: str,
    content_type: str = "video/mp4",
) -> Optional[str]:
    """
    Upload a local file to Amazon S3 asynchronously.
    Returns the cloud URL, or None if S3 is not configured.
    """
    if not is_s3_configured() or not local_path.exists():
        return None

    try:
        return await asyncio.to_thread(_sync_upload, local_path, s3_key, content_type)
    except Exception as e:
        logger.error(f"❌ Failed to upload {local_path.name} to S3: {e}")
        return None


async def upload_video_to_s3(local_video_path: Path, filename: str) -> str:
    """
    Upload an MP4 video to S3.
    If S3 is not configured, gracefully returns the standard local server URL.
    """
    s3_key = f"videos/{filename}"
    s3_url = await upload_file_to_s3(local_video_path, s3_key, content_type="video/mp4")

    if s3_url:
        return s3_url

    # Fallback to local server streaming URL
    return f"/videos/{filename}"


async def generate_presigned_download_url(s3_key: str, expiration: int = 86400) -> Optional[str]:
    """Generate a temporary signed download URL for private S3 buckets."""
    if not is_s3_configured():
        return None

    client = _get_s3_client()
    try:
        url = await asyncio.to_thread(
            client.generate_presigned_url,
            "get_object",
            Params={"Bucket": AWS_S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expiration,
        )
        return url
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
        return None
