"""Local raw document and metadata artifact storage manager."""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from finreg.config.settings import get_settings
from finreg.ingestion.models import RegulationMetadata

logger = logging.getLogger(__name__)


class LocalStorageManager:
    """Manager for storing raw downloaded PDF files and JSON metadata artifacts."""

    def __init__(
        self,
        raw_dir: str | Path | None = None,
        metadata_dir: str | Path | None = None,
    ):
        settings = get_settings()
        self.raw_root = Path(raw_dir or settings.raw_data_dir)
        self.metadata_root = Path(metadata_dir or settings.metadata_data_dir)

    def get_raw_storage_path(
        self,
        source: str,
        regulation_type: str,
        document_id: UUID | str,
        sha256: str,
        extension: str = "pdf",
    ) -> Path:
        """Construct deterministic storage path for a raw document file.

        Path format: data/raw/{source}/{regulation_type}/{document_id}/{sha256}.{ext}
        """
        clean_ext = extension.lstrip(".")
        return (
            self.raw_root
            / source.upper()
            / regulation_type.upper()
            / str(document_id)
            / f"{sha256}.{clean_ext}"
        )

    def get_metadata_storage_path(
        self, source: str, regulation_type: str, regulation_id: UUID | str
    ) -> Path:
        """Construct deterministic storage path for a regulation JSON metadata artifact.

        Path format: data/metadata/{source}/{regulation_type}/{regulation_id}.json
        """
        return (
            self.metadata_root / source.upper() / regulation_type.upper() / f"{regulation_id}.json"
        )

    def save_raw_file(
        self,
        content_bytes: bytes,
        source: str,
        regulation_type: str,
        document_id: UUID | str,
        sha256: str,
        extension: str = "pdf",
    ) -> str:
        """Save raw bytes to deterministic storage path and return relative/absolute string path."""
        target_path = self.get_raw_storage_path(
            source=source,
            regulation_type=regulation_type,
            document_id=document_id,
            sha256=sha256,
            extension=extension,
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content_bytes)
        logger.info("Saved raw file to %s (%d bytes)", target_path, len(content_bytes))
        return str(target_path)

    def save_metadata_artifact(
        self,
        metadata: RegulationMetadata,
        regulation_id: UUID | str,
        extra_info: dict[str, Any] | None = None,
    ) -> str:
        """Save JSON audit metadata artifact to disk."""
        target_path = self.get_metadata_storage_path(
            source=metadata.source,
            regulation_type=metadata.regulation_type,
            regulation_id=regulation_id,
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "regulation_id": str(regulation_id),
            "metadata": metadata.model_dump(mode="json"),
            "extra_info": extra_info or {},
        }

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.debug("Saved metadata artifact to %s", target_path)
        return str(target_path)

    def delete_file_if_exists(self, file_path: str | Path) -> None:
        """Safely delete a file if present (used for rollback on failure)."""
        path = Path(file_path)
        if path.exists():
            try:
                path.unlink()
                logger.info("Cleaned up file at %s", path)
            except Exception as exc:
                logger.warning("Failed to delete transient file at %s: %s", path, exc)
