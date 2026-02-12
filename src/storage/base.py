"""Interfaz abstracta de almacenamiento."""

from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    """Interfaz para backends de almacenamiento."""

    @abstractmethod
    async def save(self, data: bytes, filename: str, folder: str = "") -> str:
        """Guarda datos y retorna la ruta/URL."""
        ...

    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Lee datos desde una ruta."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Elimina un archivo."""
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Verifica si un archivo existe."""
        ...
