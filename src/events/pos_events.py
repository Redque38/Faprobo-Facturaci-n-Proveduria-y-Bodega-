"""
Eventos del módulo Punto de Venta.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class BuscarProductoPosEvent:
    """Solicita búsqueda de productos por nombre o código."""
    texto: str
    ticket_id: str


@dataclass
class VentaCompletadaEvent:
    """Se publica cuando una venta es procesada y pagada exitosamente."""
    ticket_id: str
    factura_id: int
    total: float
    metodo_pago: str
    lineas: list = field(default_factory=list)
    descuento_global: float = 0.0
