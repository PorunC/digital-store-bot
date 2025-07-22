"""Dependency Injection framework for the application."""

from .container import Container
from .decorators import inject
from .protocols import Injectable

# Create global container instance
container = Container()

__all__ = ["Container", "container", "inject", "Injectable"]