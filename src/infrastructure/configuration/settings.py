"""Application settings using Pydantic Settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseModel):
    """Bot configuration."""
    
    token: str
    domain: str
    port: int = 8080
    admins: List[int] = Field(default_factory=list)
    dev_id: int
    support_id: int


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    driver: str = "sqlite+aiosqlite"
    host: Optional[str] = None
    port: Optional[int] = None
    name: str = "digital_store"
    username: Optional[str] = None
    password: Optional[str] = None
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10

    def get_url(self) -> str:
        """Get database URL."""
        if self.driver.startswith("sqlite"):
            return f"{self.driver}:///data/{self.name}.db"
        return f"{self.driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseModel):
    """Redis configuration."""
    
    host: str = "digitalstore-redis"    # Updated from 3xui-shop default
    port: int = 6379
    db: int = 0
    username: Optional[str] = None
    password: Optional[str] = None

    def get_url(self) -> str:
        """Get Redis URL."""
        if self.username and self.password:
            return f"redis://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class TrialConfig(BaseModel):
    """Trial configuration."""
    
    enabled: bool = True
    period_days: int = 3
    referred_enabled: bool = True
    referred_period_days: int = 7


class ReferralConfig(BaseModel):
    """Referral configuration."""
    
    enabled: bool = True
    level_one_reward_days: int = 10
    level_two_reward_days: int = 3
    level_one_reward_rate: int = 50      # From SHOP_REFERRER_LEVEL_ONE_RATE
    level_two_reward_rate: int = 5       # From SHOP_REFERRER_LEVEL_TWO_RATE
    bonus_devices_count: int = 1         # From SHOP_BONUS_DEVICES_COUNT


class ShopConfig(BaseModel):
    """Shop configuration."""
    
    name: str = "Digital Store"
    email: str = "support@digitalstore.com"    # Updated from 3xui-shop default
    currency: str = "USD"                    # Updated from 3xui-shop default (RUB)
    trial: TrialConfig = Field(default_factory=TrialConfig)
    referral: ReferralConfig = Field(default_factory=ReferralConfig)


class ProductConfig(BaseModel):
    """Product configuration."""
    
    catalog_file: str = "data/products.json"    # Updated from 3xui-shop path
    default_category: str = "digital"
    delivery_timeout_seconds: int = 3600
    categories: List[str] = Field(default_factory=lambda: [
        "software", "gaming", "subscription", "digital", "education"
    ])


class TelegramStarsConfig(BaseModel):
    """Telegram Stars payment configuration."""
    
    enabled: bool = True


class CryptomusConfig(BaseModel):
    """Cryptomus payment configuration."""
    
    enabled: bool = True                                      # Updated from 3xui-shop (enabled by default)
    api_key: Optional[str] = "your_cryptomus_api_key_here"   # From CRYPTOMUS_API_KEY
    merchant_id: Optional[str] = "your_cryptomus_merchant_id_here"  # From CRYPTOMUS_MERCHANT_ID


class PaymentConfig(BaseModel):
    """Payment configuration."""
    
    telegram_stars: TelegramStarsConfig = Field(default_factory=TelegramStarsConfig)
    cryptomus: CryptomusConfig = Field(default_factory=CryptomusConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = "DEBUG"                                      # Updated from 3xui-shop default
    format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"  # From LOG_FORMAT
    file_enabled: bool = True
    file_path: str = "logs/app.log"
    file_max_bytes: int = 10485760  # 10MB
    file_backup_count: int = 5
    archive_format: str = "zip"                               # From LOG_ARCHIVE_FORMAT


class I18nConfig(BaseModel):
    """Internationalization configuration."""
    
    default_locale: str = "en"
    locales_dir: str = "locales"
    supported_locales: List[str] = Field(default_factory=lambda: ["en", "ru", "zh"])


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    secret_key: str
    token_expire_hours: int = 24
    max_requests_per_minute: int = 60


class ExternalConfig(BaseModel):
    """External services configuration."""
    
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    letsencrypt_email: str = "example@email.com"    # From LETSENCRYPT_EMAIL


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore"
    )

    # Configuration sections
    bot: BotConfig
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    shop: ShopConfig = Field(default_factory=ShopConfig)
    products: ProductConfig = Field(default_factory=ProductConfig)
    payments: PaymentConfig = Field(default_factory=PaymentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    i18n: I18nConfig = Field(default_factory=I18nConfig)
    security: SecurityConfig
    external: ExternalConfig = Field(default_factory=ExternalConfig)

    @classmethod
    def from_yaml(cls, config_path: str) -> "Settings":
        """Load settings from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)

    def save_to_yaml(self, config_path: str) -> None:
        """Save settings to YAML file."""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, indent=2)


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    config_path = os.getenv("CONFIG_PATH", "config/settings.yml")
    
    if os.path.exists(config_path):
        return Settings.from_yaml(config_path)
    
    # Fallback to environment variables
    return Settings()