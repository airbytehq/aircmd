from typing import Any, Type


class Singleton:
    _instances: dict[Type['Singleton'], Any] = {}

    def __new__(cls: Type['Singleton'], *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]
