"""
Storage service abstraction.
Supports local filesystem and S3-compatible storage.
Switch providers via STORAGE_PROVIDER env var.
"""
import uuid
from pathlib import Path

import aiofiles
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)


class StorageService:
    """
    Abstract file storage service.
    All methods are async for compatibility with FastAPI.
    """

    async def save(
        self,
        content: bytes,
        filename: str,
        subdirectory: str = "",
    ) -> str:
        """Save file bytes and return the storage reference (path or URL)."""
        if settings.STORAGE_PROVIDER == "local":
            return await self._save_local(content, filename, subdirectory)
        elif settings.STORAGE_PROVIDER == "s3":
            return await self._save_s3(content, filename, subdirectory)
        else:
            raise ValueError(f"Unknown STORAGE_PROVIDER: {settings.STORAGE_PROVIDER}")

    async def delete(self, file_path: str) -> None:
        """Delete a file from storage."""
        if settings.STORAGE_PROVIDER == "local":
            await self._delete_local(file_path)
        elif settings.STORAGE_PROVIDER == "s3":
            await self._delete_s3(file_path)

    async def _save_local(self, content: bytes, filename: str, subdirectory: str) -> str:
        """Save to local filesystem under LOCAL_STORAGE_PATH."""
        base = Path(settings.LOCAL_STORAGE_PATH)
        if subdirectory:
            base = base / subdirectory
        base.mkdir(parents=True, exist_ok=True)

        # Unique filename to avoid collisions
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = base / unique_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        log.info("File saved locally", path=str(file_path))
        return str(file_path)

    async def _delete_local(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            log.info("File deleted", path=file_path)

    async def _save_s3(self, content: bytes, filename: str, subdirectory: str) -> str:
        """Save to S3-compatible storage."""
        import boto3
        import asyncio

        key = f"{subdirectory}/{uuid.uuid4().hex}_{filename}".lstrip("/")
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        await asyncio.to_thread(
            s3.put_object,
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=content,
        )
        return f"s3://{settings.S3_BUCKET_NAME}/{key}"

    async def _delete_s3(self, file_path: str) -> None:
        import boto3
        import asyncio

        if not file_path.startswith("s3://"):
            return
        parts = file_path[5:].split("/", 1)
        bucket, key = parts[0], parts[1]
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        await asyncio.to_thread(s3.delete_object, Bucket=bucket, Key=key)
