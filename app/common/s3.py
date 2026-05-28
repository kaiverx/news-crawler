import asyncio
import uuid
from io import BytesIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import get_settings


class S3Error(Exception):
    pass


class S3Storage:

    def __init__(self):
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.endpoint = settings.s3_endpoint
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self._client.create_bucket(Bucket=self.bucket)
            except ClientError as exc:
                raise S3Error(f"Не удалось создать бакет {self.bucket}: {exc}") from exc

    async def upload_bytes(
        self, data: bytes, content_type: str, key_prefix: str = "covers"
    ) -> str:
        ext = _content_type_to_ext(content_type)
        key = f"{key_prefix}/{uuid.uuid4().hex}{ext}"

        def _upload():
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=BytesIO(data),
                ContentType=content_type,
            )

        await asyncio.to_thread(_upload)
        return f"{self.endpoint.rstrip('/')}/{self.bucket}/{key}"


def _content_type_to_ext(content_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    return mapping.get(content_type.lower(), ".bin")


_storage: S3Storage | None = None


def get_s3() -> S3Storage:
    global _storage
    if _storage is None:
        _storage = S3Storage()
        _storage.ensure_bucket()
    return _storage
