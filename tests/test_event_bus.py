"""Tests del EventBus con API dual (string y class)."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.event_bus import EventBus


@dataclass
class EventoA:
    payload: str


@dataclass
class EventoB:
    payload: int


@pytest.fixture
def bus():
    return EventBus()


# --------------------------- API por string -------------------------

def test_emit_string_llama_listener(bus):
    received = []
    bus.subscribe("hola", received.append)
    notificados = bus.emit("hola", "mundo")
    assert notificados == 1
    assert received == ["mundo"]


def test_emit_string_sin_listeners_no_falla(bus):
    assert bus.emit("nadie_escucha", None) == 0


def test_multiples_listeners_string(bus):
    a, b = [], []
    bus.subscribe("x", a.append)
    bus.subscribe("x", b.append)
    bus.emit("x", 42)
    assert a == [42] and b == [42]


# --------------------------- API por clase --------------------------

def test_publish_por_clase(bus):
    received = []
    bus.subscribe(EventoA, received.append)
    bus.publish(EventoA(payload="hola"))
    assert len(received) == 1 and received[0].payload == "hola"


def test_publish_solo_notifica_a_su_clase(bus):
    vistos_a, vistos_b = [], []
    bus.subscribe(EventoA, vistos_a.append)
    bus.subscribe(EventoB, vistos_b.append)

    bus.publish(EventoA(payload="uno"))
    bus.publish(EventoB(payload=2))

    assert len(vistos_a) == 1
    assert len(vistos_b) == 1


def test_publish_none_lanza(bus):
    with pytest.raises(ValueError):
        bus.publish(None)


# --------------------------- APIs coexisten -------------------------

def test_string_y_class_no_se_interfieren(bus):
    vistos_str, vistos_cls = [], []
    bus.subscribe("EventoA", vistos_str.append)  # topic string "EventoA"
    bus.subscribe(EventoA, vistos_cls.append)    # topic class EventoA

    # publish -> solo listener por clase
    bus.publish(EventoA(payload="via-publish"))
    # emit("EventoA", ...) -> solo listener por string
    bus.emit("EventoA", {"via": "emit"})

    assert len(vistos_cls) == 1 and vistos_cls[0].payload == "via-publish"
    assert len(vistos_str) == 1 and vistos_str[0] == {"via": "emit"}


# --------------------------- Robustez -------------------------------

def test_listener_con_excepcion_no_interrumpe_a_los_demas(bus):
    buenos = []

    def malo(_):
        raise RuntimeError("boom")

    bus.subscribe("t", malo)
    bus.subscribe("t", buenos.append)

    notificados = bus.emit("t", 1)
    # El listener malo cuenta como no-notificado, el bueno sí
    assert notificados == 1
    assert buenos == [1]


def test_unsubscribe_remueve(bus):
    received = []
    bus.subscribe("u", received.append)
    assert bus.unsubscribe("u", received.append) is True
    bus.emit("u", 99)
    assert received == []
    # Segundo unsubscribe no encuentra, devuelve False
    assert bus.unsubscribe("u", received.append) is False


def test_clear(bus):
    bus.subscribe("a", lambda _: None)
    bus.subscribe(EventoA, lambda _: None)
    bus.clear()
    assert bus.emit("a", 1) == 0
    assert bus.publish(EventoA(payload="x")) == 0


def test_subscribe_topic_invalido_lanza(bus):
    with pytest.raises(TypeError):
        bus.subscribe(123, lambda _: None)  # type: ignore[arg-type]


def test_desuscripcion_durante_dispatch(bus):
    """Un handler puede des-suscribirse durante la ejecución sin romper el loop."""
    llamados = []

    def h1(payload):
        llamados.append("h1")
        bus.unsubscribe("t", h1)

    def h2(payload):
        llamados.append("h2")

    bus.subscribe("t", h1)
    bus.subscribe("t", h2)
    bus.emit("t", None)
    # Ambos se ejecutaron en esta corrida
    assert llamados == ["h1", "h2"]
    # En la siguiente emisión h1 ya no está
    llamados.clear()
    bus.emit("t", None)
    assert llamados == ["h2"]
