"""Telegram bot handlers."""

from .start import start_router
from .catalog import catalog_router
from .profile import profile_router
from .payment import payment_router
from .admin import admin_router
from .support import support_router

__all__ = [
    "start_router",
    "catalog_router",
    "profile_router", 
    "payment_router",
    "admin_router",
    "support_router"
]