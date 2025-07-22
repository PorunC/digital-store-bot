"""Decorators for dependency injection."""

import functools
from typing import Any, Callable, TypeVar

from .container import container

F = TypeVar("F", bound=Callable[..., Any])


def inject(func: F) -> F:
    """Decorator to inject dependencies into a function or method."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        injected_func = container._inject_dependencies(func)
        return injected_func(*args, **kwargs)
    
    return wrapper


def singleton(cls: type) -> type:
    """Decorator to make a class a singleton."""
    cls._instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = container.resolve(cls)
        return cls._instance
    
    cls.get_instance = get_instance
    return cls


def service(interface: type = None):
    """Decorator to register a class as a service."""
    
    def decorator(cls: type) -> type:
        target_interface = interface or cls
        container.register_transient(target_interface, cls)
        return cls
    
    return decorator