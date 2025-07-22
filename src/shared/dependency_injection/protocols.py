"""Protocols for dependency injection."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Injectable(Protocol):
    """Protocol for classes that can be injected as dependencies."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the injectable class."""
        ...


@runtime_checkable
class Singleton(Protocol):
    """Protocol for singleton classes."""

    _instance: "Singleton | None"

    @classmethod
    def get_instance(cls) -> "Singleton":
        """Get the singleton instance."""
        ...


@runtime_checkable
class Configurable(Protocol):
    """Protocol for configurable classes."""

    def configure(self, **kwargs) -> None:
        """Configure the class with provided parameters."""
        ...