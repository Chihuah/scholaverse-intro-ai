"""Storage service interface for communicating with vm-db-storage."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PLACEHOLDER_DIR = settings.STATIC_DIR / "images" / "placeholder"


class StorageService(ABC):
    """Abstract interface for vm-db-storage communication."""

    @abstractmethod
    async def get_image(self, image_path: str) -> bytes:
        """Read image file from storage."""

    @abstractmethod
    async def list_images(self, student_id: int) -> list[dict]:
        """List all images for a student."""

    @abstractmethod
    async def get_metadata(self, card_id: int) -> dict:
        """Get image metadata for a card."""


class RealStorageService(StorageService):
    """Real implementation that calls vm-db-storage over HTTP."""

    def __init__(self) -> None:
        self._base_url = settings.DB_STORAGE_BASE_URL.rstrip("/")

    async def get_image(self, image_path: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._base_url}/api/images/{image_path.lstrip('/')}"
                )
                resp.raise_for_status()
                return resp.content
        except httpx.HTTPError as e:
            logger.error("Failed to get image %s: %s", image_path, e)
            raise

    async def list_images(self, student_id: int) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self._base_url}/api/images/list",
                    params={"student_id": student_id},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error("Failed to list images for student %d: %s", student_id, e)
            return []

    async def get_metadata(self, card_id: int) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self._base_url}/api/metadata/{card_id}"
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error("Failed to get metadata for card %d: %s", card_id, e)
            return {"error": str(e)}


class MockStorageService(StorageService):
    """Mock implementation for development without vm-db-storage."""

    async def get_image(self, image_path: str) -> bytes:
        placeholder = PLACEHOLDER_DIR / "card_placeholder.svg"
        if placeholder.exists():
            return placeholder.read_bytes()
        # Fallback: return minimal SVG bytes
        return b'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="420"><rect width="300" height="420" fill="#1a1a2e"/></svg>'

    async def list_images(self, student_id: int) -> list[dict]:
        return [
            {
                "image_path": f"/students/{student_id}/cards/card_001.png",
                "thumbnail_path": f"/students/{student_id}/cards/card_001_thumb.png",
                "card_id": 1,
                "created_at": "2026-02-10T10:00:00Z",
            },
            {
                "image_path": f"/students/{student_id}/cards/card_002.png",
                "thumbnail_path": f"/students/{student_id}/cards/card_002_thumb.png",
                "card_id": 2,
                "created_at": "2026-02-14T14:30:00Z",
            },
        ]

    async def get_metadata(self, card_id: int) -> dict:
        return {
            "card_id": card_id,
            "prompt": "16-bit pixel art, fantasy RPG character card, elf mage in legendary robe",
            "model": "flux.1-dev (mock)",
            "dimensions": {"width": 768, "height": 1024},
            "file_size_bytes": 524288,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Singleton instances
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Factory: returns mock or real storage service based on config."""
    global _storage_service
    if _storage_service is None:
        if settings.USE_MOCK_STORAGE:
            logger.info("Using MockStorageService")
            _storage_service = MockStorageService()
        else:
            logger.info("Using RealStorageService -> %s", settings.DB_STORAGE_BASE_URL)
            _storage_service = RealStorageService()
    return _storage_service
