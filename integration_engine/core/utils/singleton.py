from abc import ABCMeta
from typing import Any, Dict, Type, TypeVar, Optional


class SingletonMeta(type):
    """
    This is a thread-safe implementation of Singleton that can be combined with ABCMeta.
    """
    _instances: Dict[type, Any] = {}
    _lock: Any = None  # Will be set to threading.Lock() when needed

    def __call__(cls, *args, **kwargs):
        # Import here to avoid potential circular imports
        import threading
        
        # Initialize the lock if it hasn't been initialized yet
        if cls._lock is None:
            cls._lock = threading.Lock()
        
        # Double-checked locking pattern to ensure thread safety
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


# Create a combined metaclass that works with ABC
class ABCSingletonMeta(ABCMeta, SingletonMeta):
    """
    A metaclass that combines ABCMeta and SingletonMeta to support both ABC and Singleton patterns.
    """
    pass


class Singleton(metaclass=SingletonMeta):
    """
    A base class that ensures only one instance of the class exists.
    """
    pass
