"""Product-related value objects."""

from enum import Enum
from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, Field, validator

if TYPE_CHECKING:
    from ..entities.product import Product


class DeliveryType(str, Enum):
    """Product delivery types."""
    LICENSE_KEY = "license_key"
    ACCOUNT_INFO = "account_info"
    DOWNLOAD_LINK = "download_link"
    DIGITAL = "digital"
    API = "api"


class ProductInfo(BaseModel):
    """Product information value object."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1000)
    short_description: Optional[str] = Field(None, max_length=200)

    class Config:
        """Pydantic configuration."""
        frozen = True

    @validator("name")
    def validate_name(cls, v):
        """Validate product name."""
        if not v or not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip()

    @validator("description")
    def validate_description(cls, v):
        """Validate product description."""
        if not v or not v.strip():
            raise ValueError("Product description cannot be empty")
        return v.strip()

    @validator("short_description")
    def validate_short_description(cls, v):
        """Validate short description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @property
    def display_description(self) -> str:
        """Get description for display (short if available, otherwise full)."""
        return self.short_description or self.description


class DeliveryData(BaseModel):
    """Delivery data for products."""

    delivery_type: DeliveryType
    license_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    download_url: Optional[str] = None
    api_key: Optional[str] = None
    additional_info: Optional[str] = None

    class Config:
        """Pydantic configuration."""
        frozen = True

    @validator("license_key")
    def validate_license_key(cls, v, values):
        """Validate license key when delivery type is LICENSE_KEY."""
        delivery_type = values.get("delivery_type")
        if delivery_type == DeliveryType.LICENSE_KEY and not v:
            raise ValueError("License key is required for license key delivery")
        return v

    @validator("username")
    def validate_username(cls, v, values):
        """Validate username when delivery type is ACCOUNT_INFO."""
        delivery_type = values.get("delivery_type")
        if delivery_type == DeliveryType.ACCOUNT_INFO and not v:
            raise ValueError("Username is required for account info delivery")
        return v

    @validator("download_url")
    def validate_download_url(cls, v, values):
        """Validate download URL when delivery type is DOWNLOAD_LINK."""
        delivery_type = values.get("delivery_type")
        if delivery_type == DeliveryType.DOWNLOAD_LINK and not v:
            raise ValueError("Download URL is required for download link delivery")
        return v

    @validator("api_key")
    def validate_api_key(cls, v, values):
        """Validate API key when delivery type is API."""
        delivery_type = values.get("delivery_type")
        if delivery_type == DeliveryType.API and not v:
            raise ValueError("API key is required for API delivery")
        return v

    def get_delivery_message(self, template: str) -> str:
        """Format delivery message using template."""
        format_data = {}
        
        if self.license_key:
            format_data["license_key"] = self.license_key
        if self.username:
            format_data["username"] = self.username
        if self.password:
            format_data["password"] = self.password
        if self.download_url:
            format_data["download_url"] = self.download_url
        if self.api_key:
            format_data["api_key"] = self.api_key
        if self.additional_info:
            format_data["additional_info"] = self.additional_info

        try:
            return template.format(**format_data)
        except KeyError as e:
            raise ValueError(f"Template contains unknown placeholder: {e}")


class ProductFilter(BaseModel):
    """Product filtering criteria."""

    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: Optional[str] = None
    available_only: bool = True
    search_query: Optional[str] = None

    def matches_product(self, product: "Product") -> bool:
        """Check if product matches filter criteria."""
        category_value = product.category.value if hasattr(product.category, 'value') else str(product.category)
        if self.category and category_value != self.category:
            return False
            
        if self.available_only and not product.is_available:
            return False
            
        if self.min_price and float(product.price.amount) < self.min_price:
            return False
            
        if self.max_price and float(product.price.amount) > self.max_price:
            return False
            
        if self.currency and product.price.currency != self.currency:
            return False
            
        if self.search_query:
            query = self.search_query.lower()
            if (query not in product.name.lower() and 
                query not in product.description.lower()):
                return False
                
        return True