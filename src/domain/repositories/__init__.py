"""Domain repository interfaces."""

from .base import Repository, UnitOfWork
from .user_repository import UserRepository
from .product_repository import ProductRepository
from .order_repository import OrderRepository
from .referral_repository import ReferralRepository
from .invite_repository import InviteRepository
from .promocode_repository import PromocodeRepository

__all__ = [
    "Repository",
    "UnitOfWork", 
    "UserRepository",
    "ProductRepository",
    "OrderRepository",
    "ReferralRepository",
    "InviteRepository",
    "PromocodeRepository"
]