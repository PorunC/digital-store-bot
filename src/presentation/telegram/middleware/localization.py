"""Localization middleware for multi-language support."""

import logging
from typing import Dict, Any, Callable, Awaitable, Optional
from pathlib import Path

from aiogram import BaseMiddleware
from aiogram.types import Update
from fluent.runtime import FluentLocalization, FluentResourceLoader

from src.application.services import UserApplicationService
from src.core.containers import ApplicationContainer

logger = logging.getLogger(__name__)


class LocalizationMiddleware(BaseMiddleware):
    """
    Middleware for handling multi-language localization.
    """
    
    def __init__(self, container: ApplicationContainer, locales_path: str = "locales", default_locale: str = "en"):
        self.container = container
        self.locales_path = Path(locales_path)
        self.default_locale = default_locale
        self.locales: Dict[str, FluentLocalization] = {}
        self.fallback_texts: Dict[str, str] = {}
        
        # Load localization files
        self._load_locales()
        
        # Supported languages
        self.supported_locales = {
            "en": "English",
            "ru": "Русский", 
            "zh": "中文",
            "es": "Español",
            "de": "Deutsch",
            "fr": "Français",
            "it": "Italiano",
            "pt": "Português",
            "ja": "日本語",
            "ko": "한국어"
        }
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Process update through localization middleware."""
        
        # Get user language preference
        user_locale = await self._get_user_locale(event)
        
        # Create localization instance
        l10n = self._get_localization(user_locale)
        
        # Add localization functions to data
        data["l10n"] = l10n
        data["_"] = lambda key, **kwargs: self._translate(l10n, key, **kwargs)
        data["user_locale"] = user_locale
        data["supported_locales"] = self.supported_locales
        
        return await handler(event, data)
    
    def _load_locales(self) -> None:
        """Load all localization files."""
        try:
            if not self.locales_path.exists():
                logger.warning(f"Locales directory not found: {self.locales_path}")
                self._create_default_locales()
                return
            
            loader = FluentResourceLoader(str(self.locales_path))
            
            for locale_dir in self.locales_path.iterdir():
                if locale_dir.is_dir():
                    locale_code = locale_dir.name
                    try:
                        # Load .ftl files for this locale
                        ftl_files = list(locale_dir.glob("*.ftl"))
                        if ftl_files:
                            resources = [str(f.relative_to(self.locales_path)) for f in ftl_files]
                            self.locales[locale_code] = FluentLocalization(
                                [locale_code], 
                                resource_ids=resources,
                                resource_loader=loader
                            )
                            logger.info(f"Loaded locale: {locale_code}")
                    except Exception as e:
                        logger.error(f"Error loading locale {locale_code}: {e}")
            
            # Load fallback texts if no Fluent files available
            if not self.locales:
                self._create_fallback_texts()
                
        except Exception as e:
            logger.error(f"Error loading locales: {e}")
            self._create_fallback_texts()
    
    def _create_default_locales(self) -> None:
        """Create default locale files if they don't exist."""
        try:
            # Create locales directory
            self.locales_path.mkdir(parents=True, exist_ok=True)
            
            # Create English locale
            en_dir = self.locales_path / "en"
            en_dir.mkdir(exist_ok=True)
            
            default_messages = """
# Common messages
welcome = Welcome to Digital Store Bot!
help = Here's how to use the bot...
error = An error occurred. Please try again.

# Commands
start-command = Start the bot
catalog-command = Browse products
profile-command = View your profile
orders-command = Order history
help-command = Get help
support-command = Contact support

# Buttons
back-button = 🔙 Back
cancel-button = ❌ Cancel
confirm-button = ✅ Confirm
refresh-button = 🔄 Refresh

# Product catalog
catalog-title = 📦 Product Catalog
product-price = Price: ${$amount} {$currency}
product-duration = Duration: {$days} days
buy-product = 💳 Buy Now

# Profile
profile-title = 👤 Your Profile
subscription-active = 💎 Active: {$type}
subscription-expires = ⏰ Expires: {$date}
subscription-free = 🆓 Free account

# Payment
payment-success = 🎉 Payment successful!
payment-failed = ❌ Payment failed
order-created = 🛍️ Order created
payment-pending = ⏳ Payment pending

# Errors
user-not-found = User not found
product-not-found = Product not found
order-not-found = Order not found
insufficient-stock = Insufficient stock
payment-error = Payment processing error

# Admin
admin-panel = 🔧 Admin Panel
admin-stats = 📊 Statistics  
admin-users = 👥 Users
admin-products = 📦 Products
admin-orders = 🛍️ Orders

# Support
support-title = 📞 Support
faq-title = 📋 FAQ
ticket-created = ✅ Support ticket created
"""
            
            with open(en_dir / "messages.ftl", "w", encoding="utf-8") as f:
                f.write(default_messages)
            
            logger.info("Created default English locale files")
            
        except Exception as e:
            logger.error(f"Error creating default locales: {e}")
    
    def _create_fallback_texts(self) -> None:
        """Create fallback text dictionary."""
        self.fallback_texts = {
            "welcome": "Welcome to Digital Store Bot!",
            "help": "Here's how to use the bot...",
            "error": "An error occurred. Please try again.",
            "back-button": "🔙 Back",
            "cancel-button": "❌ Cancel",
            "confirm-button": "✅ Confirm",
            "refresh-button": "🔄 Refresh",
            "catalog-title": "📦 Product Catalog",
            "profile-title": "👤 Your Profile",
            "payment-success": "🎉 Payment successful!",
            "payment-failed": "❌ Payment failed",
            "admin-panel": "🔧 Admin Panel",
            "support-title": "📞 Support"
        }
        logger.info("Using fallback texts for localization")
    
    async def _get_user_locale(self, event: Update) -> str:
        """Get user's preferred locale."""
        try:
            # Get user from database
            user_service: UserApplicationService = self.container.user_service()
            
            user_id = None
            telegram_locale = None
            
            # Extract user info from different update types
            if hasattr(event, 'message') and event.message and hasattr(event.message, 'from_user') and event.message.from_user:
                user_id = event.message.from_user.id
                telegram_locale = event.message.from_user.language_code
            elif hasattr(event, 'callback_query') and event.callback_query and hasattr(event.callback_query, 'from_user') and event.callback_query.from_user:
                user_id = event.callback_query.from_user.id
                telegram_locale = event.callback_query.from_user.language_code
            elif hasattr(event, 'inline_query') and event.inline_query and hasattr(event.inline_query, 'from_user') and event.inline_query.from_user:
                user_id = event.inline_query.from_user.id
                telegram_locale = event.inline_query.from_user.language_code
            elif hasattr(event, 'pre_checkout_query') and event.pre_checkout_query and hasattr(event.pre_checkout_query, 'from_user') and event.pre_checkout_query.from_user:
                user_id = event.pre_checkout_query.from_user.id
                telegram_locale = event.pre_checkout_query.from_user.language_code
            
            if user_id:
                user = await user_service.get_user_by_telegram_id(user_id)
                if user and user.profile.language_code:
                    # Use user's saved preference
                    return user.profile.language_code
            
            # Fallback to Telegram's language
            if telegram_locale and telegram_locale in self.supported_locales:
                return telegram_locale
            
        except Exception as e:
            logger.error(f"Error getting user locale: {e}")
        
        return self.default_locale
    
    def _get_localization(self, locale: str) -> Optional[FluentLocalization]:
        """Get localization instance for locale."""
        return self.locales.get(locale) or self.locales.get(self.default_locale)
    
    def _translate(self, l10n: Optional[FluentLocalization], key: str, **kwargs) -> str:
        """Translate a message key."""
        try:
            if l10n:
                # Try Fluent localization
                message = l10n.format_value(key, kwargs)
                if message and message != key:
                    return message
            
            # Fallback to simple text replacement
            text = self.fallback_texts.get(key, key)
            
            # Simple variable substitution
            for var_key, var_value in kwargs.items():
                text = text.replace(f"{{{var_key}}}", str(var_value))
                text = text.replace(f"${{{var_key}}}", str(var_value))
            
            return text
            
        except Exception as e:
            logger.error(f"Error translating key '{key}': {e}")
            return key
    
    def get_available_locales(self) -> Dict[str, str]:
        """Get list of available locales."""
        return self.supported_locales.copy()
    
    def is_locale_supported(self, locale: str) -> bool:
        """Check if locale is supported."""
        return locale in self.supported_locales
    
    def add_fallback_text(self, key: str, text: str) -> None:
        """Add fallback text for a key."""
        self.fallback_texts[key] = text
    
    def get_locale_stats(self) -> Dict[str, Any]:
        """Get localization statistics."""
        return {
            "loaded_locales": list(self.locales.keys()),
            "supported_locales": list(self.supported_locales.keys()),
            "default_locale": self.default_locale,
            "fallback_texts_count": len(self.fallback_texts),
            "fluent_locales_count": len(self.locales)
        }


# Helper functions for handlers
def get_text(data: Dict[str, Any], key: str, **kwargs) -> str:
    """Get translated text from handler data."""
    translate_func = data.get("_")
    if translate_func:
        return translate_func(key, **kwargs)
    return key


def get_user_locale(data: Dict[str, Any]) -> str:
    """Get user locale from handler data."""
    return data.get("user_locale", "en")


def get_supported_locales(data: Dict[str, Any]) -> Dict[str, str]:
    """Get supported locales from handler data."""
    return data.get("supported_locales", {"en": "English"})