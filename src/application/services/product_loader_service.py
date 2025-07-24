"""Product loader service for initializing products from JSON."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal

from src.domain.entities.product import Product, ProductCategory, ProductStatus
from src.domain.repositories.base import UnitOfWork
from src.domain.value_objects.money import Money
from src.domain.value_objects.product_info import DeliveryType
from src.application.services.product_service import ProductApplicationService
from src.infrastructure.configuration.settings import Settings

logger = logging.getLogger(__name__)


class ProductLoaderService:
    """Service for loading products from JSON configuration."""

    def __init__(self, unit_of_work: UnitOfWork, settings: Settings):
        self.unit_of_work = unit_of_work
        self.settings = settings
        self.product_service = ProductApplicationService(unit_of_work)

    async def load_products_from_json(self, force_reload: bool = False) -> int:
        """Load products from JSON file into database.
        
        Args:
            force_reload: If True, reload all products even if they exist
            
        Returns:
            Number of products loaded
        """
        try:
            # Check if products already exist
            if not force_reload:
                existing_products = await self.product_service.get_all_products()
                if existing_products:
                    logger.info(f"Found {len(existing_products)} existing products, skipping load")
                    return 0

            # Load JSON data
            json_data = self._load_json_file()
            if not json_data:
                logger.error("Failed to load product JSON data")
                return 0

            # Parse and create products
            products_data = json_data.get("products", [])
            categories_data = json_data.get("categories", [])
            
            logger.info(f"Loading {len(products_data)} products from JSON")
            
            loaded_count = 0
            for product_data in products_data:
                try:
                    await self._create_product_from_data(product_data, categories_data)
                    loaded_count += 1
                except Exception as e:
                    import traceback
                    logger.error(f"Failed to create product {product_data.get('id', 'unknown')}: {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    continue

            logger.info(f"Successfully loaded {loaded_count} products")
            return loaded_count

        except Exception as e:
            logger.error(f"Error loading products from JSON: {e}")
            return 0

    def _load_json_file(self) -> Optional[Dict[str, Any]]:
        """Load JSON data from file."""
        catalog_file = self.settings.products.catalog_file
        
        # Try absolute path first
        json_path = Path(catalog_file)
        if not json_path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            json_path = project_root / catalog_file
        
        if not json_path.exists():
            logger.error(f"Product catalog file not found: {catalog_file}")
            return None

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON file {json_path}: {e}")
            return None

    async def _create_product_from_data(
        self, 
        product_data: Dict[str, Any],
        categories_data: List[Dict[str, Any]]
    ) -> Product:
        """Create a product from JSON data."""
        # Map category ID to category info
        category_map = {cat["id"]: cat for cat in categories_data}
        
        # Basic product info
        product_id = product_data["id"]
        name = product_data["name"]
        description = product_data["description"]
        
        # Category
        category_id = product_data.get("category_id") or product_data.get("category")
        
        # Validate category exists in our enum
        try:
            category = ProductCategory(category_id)
        except ValueError:
            logger.warning(f"Unknown category {category_id} for product {product_id}, using digital as fallback")
            category = ProductCategory.DIGITAL
        
        # Price
        price_amount = Decimal(str(product_data["price"]))
        price_currency = product_data.get("currency", "USD")
        price = Money(amount=price_amount, currency=price_currency)
        
        # Duration
        duration_days = product_data.get("duration_days", 30)
        
        # Delivery type mapping
        delivery_type_str = product_data.get("delivery_type", "automatic")
        delivery_type_map = {
            "automatic": DeliveryType.LICENSE_KEY,
            "manual": DeliveryType.ACCOUNT_INFO,
            "digital": DeliveryType.DIGITAL,
            "license_key": DeliveryType.LICENSE_KEY,
            "account_info": DeliveryType.ACCOUNT_INFO,
            "download_link": DeliveryType.DOWNLOAD_LINK,
            "api": DeliveryType.API,
            "physical": DeliveryType.DIGITAL  # Map physical to digital for now
        }
        delivery_type = delivery_type_map.get(delivery_type_str, DeliveryType.DIGITAL)
        
        # Stock
        stock = product_data.get("stock", 1000)
        
        # Status
        is_active = product_data.get("is_active", True)
        status = ProductStatus.ACTIVE if is_active else ProductStatus.INACTIVE
        
        # Delivery template
        metadata = product_data.get("metadata", {})
        delivery_template = metadata.get("delivery_template") or product_data.get("delivery_template", "Your product has been activated successfully! Thank you for your purchase.")
        
        # Additional metadata
        features = metadata.get("features", [])
        tags = metadata.get("tags", [])
        additional_metadata = {
            "features": features,
            "tags": tags,
            "is_featured": product_data.get("is_featured", False),
            "is_bestseller": product_data.get("is_bestseller", False),
            "sort_order": product_data.get("sort_order", 100),
            **{k: v for k, v in metadata.items() if k not in ["delivery_template", "features", "tags"]}
        }

        # Check if product already exists
        existing_product = await self.product_service.get_product_by_id(product_id)
        if existing_product:
            logger.info(f"Product {product_id} already exists, skipping")
            return existing_product

        # Create the product using domain entity
        product = Product.create(
            name=name,
            description=description,
            category=category,
            price=price,
            duration_days=duration_days,
            delivery_type=delivery_type,
            delivery_template=delivery_template,
            stock=stock,
            metadata=additional_metadata
        )
        
        # Override the ID to match JSON
        product._id = product_id  # Direct assignment to match JSON ID
        product._status = status
        
        # Add to repository
        async with self.unit_of_work:
            product_repo = self.product_service._get_product_repository()
            saved_product = await product_repo.add(product)
            await self.unit_of_work.commit()
            
        logger.info(f"Created product: {name} ({product_id})")
        return saved_product

    async def reload_products(self) -> int:
        """Reload all products from JSON, replacing existing ones."""
        try:
            # Delete all existing products
            existing_products = await self.product_service.get_all_products()
            for product in existing_products:
                await self.product_service.delete_product(product.id)
            
            logger.info(f"Deleted {len(existing_products)} existing products")
            
            # Load fresh products
            return await self.load_products_from_json(force_reload=True)
            
        except Exception as e:
            logger.error(f"Error reloading products: {e}")
            return 0