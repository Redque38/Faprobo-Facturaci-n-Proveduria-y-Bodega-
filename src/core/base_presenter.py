from abc import ABC, abstractmethod
from core.event_bus import EventBus

class BasePresenter(ABC):
    """Clase base para todos los Presenters"""
    def __init__(self, model, view, event_bus: EventBus):
        self.model = model
        self.view = view
        self.event_bus = event_bus
        self._connect_events()

    @abstractmethod
    def _connect_events(self):
        """Aquí se suscriben los eventos específicos de cada presenter"""
        pass