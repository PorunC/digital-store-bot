"""SQLAlchemy Product repository implementation."""

import uuid
from typing import List, Optional

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.product import Product, ProductCategory, ProductStatus
from src.domain.repositories.product_repository import ProductRepository
from src.domain.value_objects.money import Money
from src.domain.value_objects.product_info import DeliveryType
from ..models.product import ProductModel


class SqlAlchemyProductRepository(ProductRepository):
    """SQLAlchemy implementation of Product repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: str) -> Optional[Product]:
        """Get product by ID."""
        try:
            product_uuid = uuid.UUID(entity_id)
        except ValueError:
            return None

        stmt = select(ProductModel).where(ProductModel.id == product_uuid)
        result = await self.session.execute(stmt)
        product_model = result.scalar_one_or_none()
        
        if product_model:
            return self._model_to_entity(product_model)
        return None

    async def get_all(self) -> List[Product]:
        """Get all products."""
        stmt = select(ProductModel).order_by(ProductModel.name)
        result = await self.session.execute(stmt)
        product_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in product_models]

    async def add(self, entity: Product) -> Product:
        """Add a new product."""
        product_model = self._entity_to_model(entity)
        self.session.add(product_model)
        await self.session.flush()
        await self.session.refresh(product_model)
        
        return self._model_to_entity(product_model)

    async def update(self, entity: Product) -> Product:
        """Update an existing product."""
        stmt = select(ProductModel).where(ProductModel.id == entity.id)
        result = await self.session.execute(stmt)
        product_model = result.scalar_one_or_none()
        
        if not product_model:
            raise ValueError(f"Product with ID {entity.id} not found")

        # Update fields
        product_model.name = entity.name
        product_model.description = entity.description
        product_model.category = entity.category.value
        product_model.price_amount = entity.price.amount
        product_model.price_currency = entity.price.currency
        product_model.duration_days = entity.duration_days
        product_model.delivery_type = entity.delivery_type.value
        product_model.delivery_template = entity.delivery_template
        product_model.key_format = entity.key_format
        product_model.stock = entity.stock
        product_model.status = entity.status.value
        product_model.extra_data = entity.metadata
        product_model.version = entity.version

        await self.session.flush()
        return self._model_to_entity(product_model)

    async def delete(self, entity_id: str) -> bool:
        """Delete a product by ID."""
        try:
            product_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(ProductModel).where(ProductModel.id == product_uuid)
        result = await self.session.execute(stmt)
        product_model = result.scalar_one_or_none()
        
        if product_model:
            await self.session.delete(product_model)
            return True
        return False

    async def exists(self, entity_id: str) -> bool:
        """Check if product exists."""
        try:
            product_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(ProductModel.id).where(ProductModel.id == product_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_by_category(self, category: ProductCategory) -> List[Product]:
        """Find products by category."""
        stmt = select(ProductModel).where(
            ProductModel.category == category.value
        ).order_by(ProductModel.name)
        
        result = await self.session.execute(stmt)
        product_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in product_models]

    async def find_available(self) -> List[Product]:
        """Find available products."""
        stmt = select(ProductModel).where(
            ProductModel.status == ProductStatus.ACTIVE.value,
            or_(ProductModel.stock == -1, ProductModel.stock > 0)
        ).order_by(ProductModel.name)
        
        result = await self.session.execute(stmt)
        product_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in product_models]

    async def find_by_name(self, name: str) -> Optional[Product]:
        """Find product by name."""
        stmt = select(ProductModel).where(ProductModel.name == name)
        result = await self.session.execute(stmt)
        product_model = result.scalar_one_or_none()
        
        if product_model:
            return self._model_to_entity(product_model)
        return None

    async def search(self, query: str) -> List[Product]:
        """Search products by query."""
        search_term = f"%{query.lower()}%"
        
        stmt = select(ProductModel).where(
            or_(
                func.lower(ProductModel.name).contains(search_term),
                func.lower(ProductModel.description).contains(search_term)
            )
        ).order_by(ProductModel.name)
        
        result = await self.session.execute(stmt)
        product_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in product_models]

    async def find_low_stock(self, threshold: int = 10) -> List[Product]:
        """Find products with low stock."""
        stmt = select(ProductModel).where(
            ProductModel.stock != -1,  # Not unlimited
            ProductModel.stock <= threshold,
            ProductModel.status == ProductStatus.ACTIVE.value
        ).order_by(ProductModel.stock)
        
        result = await self.session.execute(stmt)
        product_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in product_models]

    async def get_categories(self) -> List[str]:
        """Get all product categories."""
        stmt = select(ProductModel.category).distinct().order_by(ProductModel.category)
        result = await self.session.execute(stmt)
        categories = result.scalars().all()
        
        return list(categories)

    def _model_to_entity(self, model: ProductModel) -> Product:
        """Convert ProductModel to Product entity."""
        money = Money(amount=model.price_amount, currency=model.price_currency)
        
        product = Product(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            name=model.name,
            description=model.description,
            category=ProductCategory(model.category),
            price=money,
            duration_days=model.duration_days,
            delivery_type=DeliveryType(model.delivery_type),
            delivery_template=model.delivery_template,
            key_format=model.key_format,
            stock=model.stock,
            status=ProductStatus(model.status),
            metadata=model.extra_data or {}
        )

        # Clear domain events as they come from persistence
        product.clear_domain_events()
        return product

    def _entity_to_model(self, entity: Product) -> ProductModel:
        """Convert Product entity to ProductModel."""
        return ProductModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
            name=entity.name,
            description=entity.description,
            category=entity.category.value if hasattr(entity.category, 'value') else str(entity.category),
            price_amount=entity.price.amount,
            price_currency=entity.price.currency,
            duration_days=entity.duration_days,
            delivery_type=entity.delivery_type.value if hasattr(entity.delivery_type, 'value') else str(entity.delivery_type),
            delivery_template=entity.delivery_template,
            key_format=entity.key_format,
            stock=entity.stock,
            status=entity.status.value if hasattr(entity.status, 'value') else str(entity.status),
            extra_data=entity.metadata
        )