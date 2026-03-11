"""Google Cloud Storage upload service for session outputs.

Uploads interview session exports to GCS after session completion.
Skips silently when GCS_BUCKET is not configured (local dev mode).
Uses Application Default Credentials (ADC) — automatic on Cloud Run.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

import structlog

log = structlog.get_logger(__name__)


class GCSUploadService:
    """Uploads session data to Google Cloud Storage."""

    def __init__(self, bucket_name: str):
        self._bucket_name = bucket_name

    async def upload_session(self, session_id: str, data: str) -> Optional[str]:
        """Upload session JSON to GCS.

        Args:
            session_id: Session ID for path construction
            data: JSON string to upload

        Returns:
            GCS path (gs://bucket/path) on success, None if bucket not configured
        """
        if not self._bucket_name:
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        blob_path = f"sessions/{session_id}/{timestamp}.json"

        try:
            gcs_path = await asyncio.to_thread(self._upload_sync, blob_path, data)
            log.info(
                "gcs_upload_complete",
                session_id=session_id,
                gcs_path=gcs_path,
            )
            return gcs_path
        except Exception as e:
            log.warning(
                "gcs_upload_failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _upload_sync(self, blob_path: str, data: str) -> str:
        """Synchronous GCS upload (run in thread)."""
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(self._bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(data, content_type="application/json")
        return f"gs://{self._bucket_name}/{blob_path}"
