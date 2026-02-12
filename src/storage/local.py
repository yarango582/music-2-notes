"""Almacenamiento en sistema de archivos local."""

from pathlib import Path

import aiofiles

from src.storage.base import StorageBackend
from src.core.config import settings


class LocalStorage(StorageBackend):
    """Backend de almacenamiento en disco local."""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or settings.STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, folder: str, filename: str) -> Path:
        path = self.base_path / folder / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def save(self, data: bytes, filename: str, folder: str = "") -> str:
        path = self._resolve(folder, filename)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return str(path)

    async def read(self, path: str) -> bytes:
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            p.unlink()

    async def exists(self, path: str) -> bool:
        return Path(path).exists()

    async def save_upload(self, data: bytes, job_id: str, filename: str) -> str:
        """Guarda un archivo subido por el usuario."""
        return await self.save(data, filename, folder=f"uploads/{job_id}")

    async def save_result(self, data: bytes, job_id: str, filename: str) -> str:
        """Guarda un archivo de resultado."""
        return await self.save(data, filename, folder=f"results/{job_id}")


# Instancia global
storage = LocalStorage()
