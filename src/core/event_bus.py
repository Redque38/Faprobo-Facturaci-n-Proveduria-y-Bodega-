"""
EventBus — API dual (str y Class) para no forzar a migrar todo el código.

Convenciones soportadas:

1) Por nombre (string):
       bus.subscribe("login_success", handler)
       bus.emit("login_success", LoginSuccessEvent(...))

2) Por clase (tipo del evento):
       bus.subscribe(FacturaCreada, handler)
       bus.publish(FacturaCreada(...))     # el tópico se infiere de type(evento)

Ambas coexisten en la misma instancia de EventBus sin interferirse: se
indexan por el topic (que puede ser str o type) y cada lista de
suscriptores es independiente.

Detalles:
- Los handlers se copian antes de iterar para tolerar des/suscripciones
  mid-dispatch.
- Los errores en un handler NO interrumpen al resto: se capturan y se
  reportan por el logger `core.event_bus`.
- Hay lock interno para subscribe/unsubscribe desde varios hilos.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Union

log = logging.getLogger(__name__)

Topic = Union[str, type]
Listener = Callable[[Any], None]


class EventBus:
    """Bus de eventos central con API dual (string y class)."""

    def __init__(self) -> None:
        self._listeners: dict[Topic, list[Listener]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Suscripción
    # ------------------------------------------------------------------
    def subscribe(self, topic: Topic, listener: Listener) -> None:
        """
        Registra `listener` para el tópico indicado.
        `topic` puede ser un nombre (str) o la clase del evento (type).
        """
        if not (isinstance(topic, str) or isinstance(topic, type)):
            raise TypeError(
                f"topic debe ser str o type, no {type(topic).__name__}"
            )
        with self._lock:
            self._listeners.setdefault(topic, []).append(listener)

    def unsubscribe(self, topic: Topic, listener: Listener) -> bool:
        """Elimina una suscripción. Devuelve True si se removió."""
        with self._lock:
            handlers = self._listeners.get(topic)
            if not handlers:
                return False
            try:
                handlers.remove(listener)
                if not handlers:
                    del self._listeners[topic]
                return True
            except ValueError:
                return False

    def clear(self) -> None:
        """Elimina todas las suscripciones. Útil en tests."""
        with self._lock:
            self._listeners.clear()

    # ------------------------------------------------------------------
    # Publicación
    # ------------------------------------------------------------------
    def emit(self, topic: Topic, data: Any = None) -> int:
        """
        Despacha por nombre (clásico) o por tipo.
        Devuelve la cantidad de listeners notificados sin error.
        """
        return self._dispatch(topic, data)

    def publish(self, evento: Any) -> int:
        """
        Despacha usando la clase del evento como tópico.
        Equivalente a `emit(type(evento), evento)`.
        """
        if evento is None:
            raise ValueError("publish() requiere una instancia de evento, no None.")
        return self._dispatch(type(evento), evento)

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------
    def _dispatch(self, topic: Topic, payload: Any) -> int:
        with self._lock:
            handlers = self._listeners.get(topic, [])[:]  # copia bajo lock
        notified = 0
        for h in handlers:
            try:
                h(payload)
                notified += 1
            except Exception:
                # Un listener con bug no debería romper a los demás
                log.exception(
                    "Error en listener para topic=%r", getattr(topic, "__name__", topic)
                )
        return notified
