
from typing import Callable, Dict, Any, List

class EventBus:
    """Bus de eventos central para toda la aplicación"""
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, listener: Callable):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(listener)

    def emit(self, event_name: str, data: Any = None):
        if event_name in self._listeners:
            # Usamos copia para evitar errores si un listener se desuscribe durante la ejecución
            for listener in self._listeners[event_name][:]:
                listener(data)