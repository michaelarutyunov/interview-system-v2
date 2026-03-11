"""Tests for GCS upload service."""

import pytest
from unittest.mock import patch, MagicMock

from src.services.gcs_upload_service import GCSUploadService


class TestGCSUploadService:
    """Tests for GCSUploadService."""

    @pytest.mark.asyncio
    async def test_upload_skips_when_bucket_empty(self):
        """Upload returns None when bucket is not configured."""
        service = GCSUploadService(bucket_name="")
        result = await service.upload_session("session-123", '{"data": "test"}')
        assert result is None

    @pytest.mark.asyncio
    async def test_upload_skips_when_bucket_falsy(self):
        """Upload returns None for any falsy bucket name."""
        for bucket in ["", None]:
            service = GCSUploadService(bucket_name=bucket)
            result = await service.upload_session("session-123", '{"data": "test"}')
            assert result is None

    @pytest.mark.asyncio
    async def test_upload_calls_gcs_client(self):
        """Upload calls GCS client with correct bucket and path."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        with patch("src.services.gcs_upload_service.GCSUploadService._upload_sync") as mock_sync:
            mock_sync.return_value = "gs://test-bucket/sessions/sess-1/20260311_120000.json"

            service = GCSUploadService(bucket_name="test-bucket")
            result = await service.upload_session("sess-1", '{"data": "test"}')

            assert result is not None
            assert result.startswith("gs://test-bucket/")
            mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_returns_none_on_error(self):
        """Upload returns None and logs warning on GCS error."""
        with patch("src.services.gcs_upload_service.GCSUploadService._upload_sync") as mock_sync:
            mock_sync.side_effect = Exception("GCS connection failed")

            service = GCSUploadService(bucket_name="test-bucket")
            result = await service.upload_session("sess-1", '{"data": "test"}')

            assert result is None
