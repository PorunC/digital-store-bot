"""Decorators for event handling."""

from typing import Callable, Type

from .base import DomainEvent
from .bus import event_bus


def event_handler(event_type: str):
    """Decorator to register an event handler."""
    
    def decorator(handler_class: type) -> type:
        # Auto-register the handler when the class is defined
        handler_instance = handler_class()
        event_bus.subscribe(event_type, handler_instance)
        return handler_class
    
    return decorator


def handles_event(event_class: Type[DomainEvent]):
    """Decorator to register an event handler for a specific event class."""
    
    def decorator(handler_class: type) -> type:
        event_type = f"{event_class.__module__}.{event_class.__name__}"
        return event_handler(event_type)(handler_class)
    
    return decorator