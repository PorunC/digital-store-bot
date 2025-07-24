"""Dependency injection container implementation."""

import inspect
from typing import Any, Callable, Dict, Type, TypeVar, Union, get_type_hints

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

        # Check if it's an Optional type
        if hasattr(interface, '__origin__') and interface.__origin__ is Union:
            args = interface.__args__
            if len(args) == 2 and type(None) in args:
                # This is Optional[SomeType] - try to resolve the non-None type
                non_none_type = args[0] if args[1] is type(None) else args[1]
                try:
                    return self.resolve(non_none_type)
                except DependencyNotFound:
                    # If we can't resolve the non-None type, return None for Optional
                    return None
        
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
        
        # Try to get type hints safely with proper namespace resolution
        type_hints = {}
        try:
            # First try with the implementation's module namespace
            module = inspect.getmodule(implementation)
            globalns = getattr(module, '__dict__', {}) if module else {}
            
            # Add common imports that might be missing
            try:
                # Import all of sqlalchemy.ext.asyncio into namespace
                import sqlalchemy.ext.asyncio as asyncio_module
                for attr_name in dir(asyncio_module):
                    attr = getattr(asyncio_module, attr_name)
                    if not attr_name.startswith('_') or attr_name in ['_AsyncSessionBind', '_SessionBindKey']:
                        globalns[attr_name] = attr
                        
                # Also add some internal types that might be needed
                try:
                    from sqlalchemy.orm import Session
                    globalns['Session'] = Session
                except ImportError:
                    pass
                    
            except ImportError:
                pass
                    
            type_hints = get_type_hints(constructor, globalns=globalns)
        except (NameError, AttributeError, TypeError) as e:
            # If type hints still can't be resolved, use signature annotations directly
            try:
                # Fall back to raw annotations without evaluation
                for param_name, param in signature.parameters.items():
                    if param_name != "self" and param.annotation != inspect.Parameter.empty:
                        type_hints[param_name] = param.annotation
            except Exception:
                pass

        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue

            # First try to get from resolved type hints, then fall back to annotation
            param_type = type_hints.get(param_name, param.annotation)
            if param_type == inspect.Parameter.empty:
                if param.default != inspect.Parameter.empty:
                    continue
                raise DependencyNotFound(
                    f"Cannot resolve parameter '{param_name}' for {implementation}"
                )

            # Skip resolution for typing.Any and other unresolvable types
            if self._is_unresolvable_type(param_type):
                if param.default != inspect.Parameter.empty:
                    continue
                raise DependencyNotFound(
                    f"Cannot resolve parameter '{param_name}' for {param_type}"
                )

            kwargs[param_name] = self.resolve(param_type)

        return implementation(**kwargs)

    def _is_unresolvable_type(self, param_type: Any) -> bool:
        """Check if a type cannot be resolved by the DI container."""
        # typing.Any
        if param_type is Any:
            return True
        
        # Check for the string "typing.Any" case which can happen with forward references
        if str(param_type) == "typing.Any" or str(param_type) == "<class 'typing.Any'>":
            return True
        
        # Handle cases where param_type is actually typing.Any but might be coming from different contexts
        try:
            if str(param_type.__name__) == 'Any' or param_type.__name__ == 'Any':
                return True
        except AttributeError:
            pass
            
        # Check for typing module types that can't be instantiated
        if hasattr(param_type, '__module__') and param_type.__module__ == 'typing':
            return True
            
        # Check for generic aliases like Dict, List, etc.
        if hasattr(param_type, '__origin__'):
            # These are generic types like Dict[str, Any], List[str], etc.
            return True
        
        # Check for Union types (including Optional)
        if hasattr(param_type, '__args__') and hasattr(param_type, '__origin__'):
            return True
        
        # Safety check for any parameter type that contains 'Any' in its string representation
        param_str = str(param_type).lower()
        if 'typing.any' in param_str or 'any' in param_str and 'typing' in param_str:
            return True
            
        return False

    def _inject_dependencies(self, func: Callable[..., T]) -> Callable[..., T]:
        """Inject dependencies into a function."""
        signature = inspect.signature(func)
        
        # Try to get type hints safely
        type_hints = {}
        try:
            type_hints = get_type_hints(func)
        except (NameError, AttributeError, TypeError) as e:
            # If type hints can't be resolved, fall back to raw annotations
            for param_name, param in signature.parameters.items():
                if param.annotation != inspect.Parameter.empty:
                    type_hints[param_name] = param.annotation

        def wrapper(*args, **kwargs):
            for param_name, param in signature.parameters.items():
                if param_name in kwargs:
                    continue

                param_type = type_hints.get(param_name, param.annotation)
                if param_type != inspect.Parameter.empty and not self._is_unresolvable_type(param_type):
                    try:
                        kwargs[param_name] = self.resolve(param_type)
                    except DependencyNotFound:
                        # Skip parameters that can't be resolved instead of failing
                        continue

            return func(*args, **kwargs)

        return wrapper

    def clear(self) -> None:
        """Clear all registrations."""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        self._resolving.clear()

    def get(self, interface: Type[T]) -> T:
        """Alias for resolve() method."""
        return self.resolve(interface)