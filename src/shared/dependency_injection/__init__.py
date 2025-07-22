"""Dependency Injection framework for the application."""

from .container import Container
from .decorators import inject
from .protocols import Injectable

__all__ = ["Container", "inject", "Injectable"]