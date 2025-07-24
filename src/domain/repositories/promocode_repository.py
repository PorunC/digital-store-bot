"""Promocode repository interface."""

from abc import abstractmethod
from typing import List, Optional

from ..entities.promocode import Promocode, PromocodeType
from .base import Repository


class PromocodeRepository(Repository[Promocode]):
    """Promocode repository interface."""

    @abstractmethod
    async def find_by_code(self, code: str) -> Optional[Promocode]:
        """Find promocode by code."""
        pass

    @abstractmethod
    async def find_active_codes(self) -> List[Promocode]:
        """Find active promocodes."""
        pass

    @abstractmethod
    async def find_by_type(self, promocode_type: PromocodeType) -> List[Promocode]:
        """Find promocodes by type."""
        pass

    @abstractmethod
    async def find_expired_codes(self) -> List[Promocode]:
        """Find expired promocodes."""
        pass

    @abstractmethod
    async def find_exhausted_codes(self) -> List[Promocode]:
        """Find exhausted promocodes."""
        pass

    @abstractmethod
    async def search_codes(self, query: str) -> List[Promocode]:
        """Search promocodes by query."""
        pass

    @abstractmethod
    async def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        pass