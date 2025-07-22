"""Dependency injection container implementation."""

import inspect
from typing import Any, Callable, Dict, Type, TypeVar, get_type_hints

from .protocols import Injectable

T = TypeVar("T")


class DependencyNotFound(Exception):
    """Raised when a dependency cannot be resolved."""

    pass


class CircularDependency(Exception):
    """Raised when a circular dependency is detected."""

    pass


class Container:
    """Dependency injection container."""

    def __init__(self) -> None:
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[..., Any]] = {}
        self._resolving: set[Type] = set()

    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a singleton service."""
        if not issubclass(implementation, interface):
            raise ValueError(f"{implementation} does not implement {interface}")
        self._singletons[interface] = implementation

    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a transient service."""
        if not issubclass(implementation, interface):
            raise ValueError(f"{implementation} does not implement {interface}")
        self._services[interface] = implementation

    def register_factory(self, interface: Type[T], factory: Callable[..., T]) -> None:
        """Register a factory function for creating instances."""
        self._factories[interface] = factory

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a specific instance."""
        self._services[interface] = instance

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency."""
        if interface in self._resolving:
            raise CircularDependency(f"Circular dependency detected for {interface}")

        # Check for existing singleton instance
        if interface in self._singletons:
            singleton_class = self._singletons[interface]
            if hasattr(singleton_class, "_instance") and singleton_class._instance is not None:
                return singleton_class._instance

        # Check for factory
        if interface in self._factories:
            factory = self._factories[interface]
            return self._inject_dependencies(factory)()

        # Check for registered instance
        if interface in self._services:
            service = self._services[interface]
            if not inspect.isclass(service):
                return service

        # Try to resolve the class
        implementation = self._services.get(interface) or self._singletons.get(interface)
        if implementation is None:
            # Try to use the interface itself if it's a concrete class
            if inspect.isclass(interface) and not inspect.isabstract(interface):
                implementation = interface
            else:
                raise DependencyNotFound(f"No registration found for {interface}")

        self._resolving.add(interface)
        try:
            instance = self._create_instance(implementation)
            
            # Store singleton instance
            if interface in self._singletons:
                self._singletons[interface]._instance = instance
                
            return instance
        finally:
            self._resolving.discard(interface)

    def _create_instance(self, implementation: Type[T]) -> T:
        """Create an instance with dependency injection."""
        constructor = implementation.__init__
        signature = inspect.signature(constructor)
        type_hints = get_type_hints(constructor)

        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue

            param_type = type_hints.get(param_name, param.annotation)
            if param_type == inspect.Parameter.empty:
                if param.default != inspect.Parameter.empty:
                    continue
                raise DependencyNotFound(
                    f"Cannot resolve parameter '{param_name}' for {implementation}"
                )

            kwargs[param_name] = self.resolve(param_type)

        return implementation(**kwargs)

    def _inject_dependencies(self, func: Callable[..., T]) -> Callable[..., T]:
        """Inject dependencies into a function."""
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)

        def wrapper(*args, **kwargs):
            for param_name, param in signature.parameters.items():
                if param_name in kwargs:
                    continue

                param_type = type_hints.get(param_name, param.annotation)
                if param_type != inspect.Parameter.empty:
                    kwargs[param_name] = self.resolve(param_type)

            return func(*args, **kwargs)

        return wrapper

    def clear(self) -> None:
        """Clear all registrations."""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        self._resolving.clear()


# Global container instance
container = Container()