"""Object storage service for file uploads.

Supports local filesystem and cloud storage (S3-compatible).
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.core.config import settings


class StorageError(Exception):
    """Base exception for storage errors."""

    pass


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "",
    ) -> str:
        """Upload file and return URL/path.

        Args:
            file_data: File content as bytes
            filename: Desired filename
            content_type: MIME type
            folder: Optional folder/prefix

        Returns:
            URL or path to uploaded file
        """
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download file by path.

        Args:
            path: File path/key

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete file by path.

        Args:
            path: File path/key

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists.

        Args:
            path: File path/key

        Returns:
            True if exists
        """
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend.

    For development and testing. In production, use S3 or similar.
    """

    def __init__(self, base_path: str = "./storage") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "",
    ) -> str:
        """Upload file to local filesystem."""
        # Create folder structure
        if folder:
            folder_path = self.base_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
        else:
            folder_path = self.base_path

        # Generate unique filename to avoid collisions
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid4())[:8]
        safe_filename = f"{timestamp}_{unique_id}_{filename}"

        file_path = folder_path / safe_filename
        file_path.write_bytes(file_data)

        # Return relative path
        return str(file_path.relative_to(self.base_path))

    async def download(self, path: str) -> bytes:
        """Download file from local filesystem."""
        file_path = self.base_path / path

        if not file_path.exists():
            raise StorageError(f"File not found: {path}")

        return file_path.read_bytes()

    async def delete(self, path: str) -> bool:
        """Delete file from local filesystem."""
        file_path = self.base_path / path

        if not file_path.exists():
            return False

        file_path.unlink()
        return True

    async def exists(self, path: str) -> bool:
        """Check if file exists in local filesystem."""
        file_path = self.base_path / path
        return file_path.exists()


class S3StorageBackend(StorageBackend):
    """AWS S3 (or S3-compatible) storage backend.

    Requires boto3 and proper AWS credentials.
    """

    def __init__(
        self,
        bucket_name: str,
        region: str = "eu-west-2",  # UK region
        endpoint_url: str | None = None,
    ) -> None:
        """Initialize S3 backend.

        Args:
            bucket_name: S3 bucket name
            region: AWS region
            endpoint_url: Custom endpoint (for MinIO, DigitalOcean, etc.)
        """
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url

        # Lazy import boto3
        try:
            import boto3
            from botocore.config import Config

            config = Config(
                region_name=region,
                retries={"max_attempts": 3, "mode": "standard"},
            )

            self.client = boto3.client(
                "s3",
                config=config,
                endpoint_url=endpoint_url,
            )
        except ImportError:
            raise StorageError("boto3 is required for S3 storage. Install with: pip install boto3")

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "",
    ) -> str:
        """Upload file to S3."""
        from io import BytesIO

        # Generate key
        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        unique_id = str(uuid4())[:8]
        safe_filename = f"{unique_id}_{filename}"

        if folder:
            key = f"{folder}/{timestamp}/{safe_filename}"
        else:
            key = f"{timestamp}/{safe_filename}"

        try:
            self.client.upload_fileobj(
                BytesIO(file_data),
                self.bucket_name,
                key,
                ExtraArgs={"ContentType": content_type},
            )

            # Return S3 URL
            if self.endpoint_url:
                return f"{self.endpoint_url}/{self.bucket_name}/{key}"
            else:
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"

        except Exception as e:
            raise StorageError(f"Failed to upload to S3: {e}")

    async def download(self, path: str) -> bytes:
        """Download file from S3."""
        from io import BytesIO

        try:
            buffer = BytesIO()
            # Extract key from URL or use directly
            key = self._extract_key(path)
            self.client.download_fileobj(self.bucket_name, key, buffer)
            return buffer.getvalue()
        except Exception as e:
            raise StorageError(f"Failed to download from S3: {e}")

    async def delete(self, path: str) -> bool:
        """Delete file from S3."""
        try:
            key = self._extract_key(path)
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete from S3: {e}")

    async def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        try:
            key = self._extract_key(path)
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def _extract_key(self, path: str) -> str:
        """Extract S3 key from URL or path."""
        # If it's a full URL, extract the key
        if path.startswith("http"):
            # Remove bucket URL prefix
            parts = path.split(f"{self.bucket_name}/", 1)
            if len(parts) > 1:
                return parts[1]
            # Try endpoint URL format
            parts = path.split(f"{self.bucket_name}/", 1)
            if len(parts) > 1:
                return parts[1]
        return path


def get_storage_backend() -> StorageBackend:
    """Get configured storage backend.

    Returns LocalStorageBackend for development,
    S3StorageBackend for production.
    """
    storage_type = getattr(settings, "STORAGE_TYPE", "local")

    if storage_type == "s3":
        return S3StorageBackend(
            bucket_name=getattr(settings, "S3_BUCKET_NAME", "acucare-triage-notes"),
            region=getattr(settings, "S3_REGION", "eu-west-2"),
            endpoint_url=getattr(settings, "S3_ENDPOINT_URL", None),
        )
    else:
        storage_path = getattr(settings, "LOCAL_STORAGE_PATH", "./storage")
        return LocalStorageBackend(base_path=storage_path)
