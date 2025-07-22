"""Product repository interface."""

from abc import abstractmethod
from typing import List, Optional

from ..entities.product import Product, ProductCategory
from .base import Repository


class ProductRepository(Repository[Product]):
    """Product repository interface."""

    @abstractmethod
    async def find_by_category(self, category: ProductCategory) -> List[Product]:
        """Find products by category."""
        pass

    @abstractmethod
    async def find_available(self) -> List[Product]:
        """Find available products."""
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Product]:
        """Find product by name."""
        pass

    @abstractmethod
    async def search(self, query: str) -> List[Product]:
        """Search products by query."""
        pass

    @abstractmethod
    async def find_low_stock(self, threshold: int = 10) -> List[Product]:
        """Find products with low stock."""
        pass

    @abstractmethod
    async def get_categories(self) -> List[str]:
        """Get all product categories."""
        pass