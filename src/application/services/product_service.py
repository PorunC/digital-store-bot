"""Product application service with complete functionality."""

from typing import List, Optional

from src.domain.entities.product import Product, ProductCategory, ProductStatus
from src.domain.repositories.product_repository import ProductRepository
from src.domain.repositories.base import UnitOfWork
from src.domain.value_objects.money import Money
from src.domain.value_objects.product_info import DeliveryType
from src.shared.events import event_bus


class ProductApplicationService:
    """Product application service handling product-related operations."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        product_repository_factory = None
    ):
        self.unit_of_work = unit_of_work
        self._product_repository_factory = product_repository_factory
        
    def _get_product_repository(self) -> ProductRepository:
        """Get product repository using factory or fallback to direct creation."""
        if self._product_repository_factory and hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return self._product_repository_factory(self.unit_of_work.session)
            
        # Fallback to anti-pattern during transition period
        from src.infrastructure.database.repositories.product_repository import SqlAlchemyProductRepository
        if hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return SqlAlchemyProductRepository(self.unit_of_work.session)
        else:
            raise RuntimeError("Unit of work session not available")

    async def create_product(
        self,
        name: str,
        description: str,
        category: ProductCategory,
        price_amount: float,
        price_currency: str,
        duration_days: int,
        delivery_type: DeliveryType,
        delivery_template: Optional[str] = None,
        key_format: Optional[str] = None,
        stock: int = -1,
        metadata: Optional[dict] = None
    ) -> Product:
        """Create a new product."""
        async with self.unit_of_work:
            # Check if product with same name exists
            existing_product = await self._get_product_repository().find_by_name(name)
            if existing_product:
                raise ValueError(f"Product with name '{name}' already exists")

            price = Money(amount=price_amount, currency=price_currency)
            
            product = Product.create(
                name=name,
                description=description,
                category=category,
                price=price,
                duration_days=duration_days,
                delivery_type=delivery_type,
                delivery_template=delivery_template,
                key_format=key_format,
                stock=stock,
                metadata=metadata or {}
            )

            product = await self._get_product_repository().add(product)
            await self._publish_events(product)
            await self.unit_of_work.commit()
            return product

    async def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        async with self.unit_of_work:
            return await self._get_product_repository().get_by_id(product_id)

    async def get_product_by_name(self, name: str) -> Optional[Product]:
        """Get product by name."""
        async with self.unit_of_work:
            return await self._get_product_repository().find_by_name(name)

    async def get_all_products(self) -> List[Product]:
        """Get all products."""
        async with self.unit_of_work:
            return await self._get_product_repository().get_all()

    async def get_available_products(self) -> List[Product]:
        """Get available products."""
        async with self.unit_of_work:
            return await self._get_product_repository().find_available()

    async def get_products_by_category(self, category: ProductCategory) -> List[Product]:
        """Get products by category."""
        async with self.unit_of_work:
            return await self._get_product_repository().find_by_category(category)

    async def search_products(self, query: str) -> List[Product]:
        """Search products by query."""
        async with self.unit_of_work:
            return await self._get_product_repository().search(query)

    async def update_product(
        self,
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[ProductCategory] = None,
        price_amount: Optional[float] = None,
        price_currency: Optional[str] = None,
        duration_days: Optional[int] = None,
        delivery_type: Optional[DeliveryType] = None,
        delivery_template: Optional[str] = None,
        key_format: Optional[str] = None,
        stock: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> Product:
        """Update product information."""
        async with self.unit_of_work:
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            # Check if name is being changed and if it conflicts
            if name and name != product.name:
                existing_product = await self._get_product_repository().find_by_name(name)
                if existing_product and str(existing_product.id) != product_id:
                    raise ValueError(f"Product with name '{name}' already exists")

            # Update price if both amount and currency provided
            price = None
            if price_amount is not None and price_currency is not None:
                price = Money(amount=price_amount, currency=price_currency)
            elif price_amount is not None:
                price = Money(amount=price_amount, currency=product.price.currency)
            elif price_currency is not None:
                price = Money(amount=product.price.amount, currency=price_currency)

            product.update_details(
                name=name,
                description=description,
                category=category,
                price=price,
                duration_days=duration_days,
                delivery_type=delivery_type,
                delivery_template=delivery_template,
                key_format=key_format,
                stock=stock,
                metadata=metadata
            )

            product = await self._get_product_repository().update(product)
            await self._publish_events(product)
            await self.unit_of_work.commit()
            return product

    async def activate_product(self, product_id: str) -> Product:
        """Activate a product."""
        async with self.unit_of_work:
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            product.activate()

            product = await self._get_product_repository().update(product)
            await self._publish_events(product)
            await self.unit_of_work.commit()
            return product

    async def deactivate_product(self, product_id: str, reason: Optional[str] = None) -> Product:
        """Deactivate a product."""
        async with self.unit_of_work:
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            product.deactivate(reason)

            product = await self._get_product_repository().update(product)
            await self._publish_events(product)
            await self.unit_of_work.commit()
            return product

    async def update_stock(self, product_id: str, stock_change: int) -> Product:
        """Update product stock."""
        async with self.unit_of_work:
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            if stock_change > 0:
                product.add_stock(stock_change)
            elif stock_change < 0:
                product.reduce_stock(abs(stock_change))

            product = await self._get_product_repository().update(product)
            await self._publish_events(product)
            await self.unit_of_work.commit()
            return product

    async def check_availability(self, product_id: str, quantity: int = 1) -> bool:
        """Check if product is available for purchase."""
        async with self.unit_of_work:
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                return False

            return product.is_available() and product.has_sufficient_stock(quantity)

    async def reserve_stock(self, product_id: str, quantity: int = 1) -> Product:
        """Reserve product stock for an order."""
        async with self.unit_of_work:
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            if not product.is_available():
                raise ValueError(f"Product {product.name} is not available")

            if not product.has_sufficient_stock(quantity):
                raise ValueError(f"Insufficient stock for product {product.name}")

            product.reduce_stock(quantity)

            product = await self._get_product_repository().update(product)
            await self._publish_events(product)
            await self.unit_of_work.commit()
            return product

    async def release_stock(self, product_id: str, quantity: int = 1) -> Product:
        """Release reserved stock back to inventory."""
        async with self.unit_of_work:
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            product.add_stock(quantity)

            product = await self._get_product_repository().update(product)
            await self._publish_events(product)
            await self.unit_of_work.commit()
            return product

    async def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """Get products with low stock."""
        async with self.unit_of_work:
            return await self._get_product_repository().find_low_stock(threshold)

    async def get_product_categories(self) -> List[str]:
        """Get all product categories."""
        async with self.unit_of_work:
            return await self._get_product_repository().get_categories()

    async def delete_product(self, product_id: str) -> bool:
        """Delete a product."""
        async with self.unit_of_work:
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                return False

            # Publish deletion event before removing
            await self._publish_events(product)
            
            success = await self._get_product_repository().delete(product_id)
            if success:
                await self.unit_of_work.commit()
            
            return success

    async def _publish_events(self, product: Product) -> None:
        """Publish domain events."""
        events = product.get_domain_events()
        for event in events:
            await event_bus.publish(event)
        product.clear_domain_events()