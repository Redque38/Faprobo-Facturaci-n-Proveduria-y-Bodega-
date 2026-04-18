from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Eventos de ciclo de vida de facturas
# ---------------------------------------------------------------------------

@dataclass
class FacturaCreada:
    factura_id: int
    tipo: str                  # "venta" | "compra"
    cliente_proveedor_id: int
    total: float
    fecha: datetime = field(default_factory=datetime.now)


@dataclass
class FacturaAnulada:
    factura_id: int
    motivo: str
    fecha: datetime = field(default_factory=datetime.now)


@dataclass
class FacturaPagada:
    factura_id: int
    monto_pagado: float
    fecha: datetime = field(default_factory=datetime.now)


@dataclass
class CuotaRegistrada:
    factura_id: int
    numero_cuota: int
    monto: float
    fecha_vencimiento: datetime
    pagada: bool = False


# ---------------------------------------------------------------------------
# Eventos que afectan bodega (stock)
# ---------------------------------------------------------------------------

@dataclass
class StockSolicitado:
    """Facturación pregunta si hay stock suficiente antes de confirmar."""
    producto_id: int
    cantidad: int
    factura_id: int


@dataclass
class StockDescontado:
    """Bodega confirma que descontó el stock."""
    producto_id: int
    cantidad: int
    factura_id: int
    stock_restante: int


@dataclass
class StockInsuficiente:
    """Bodega informa que no hay stock suficiente."""
    producto_id: int
    cantidad_solicitada: int
    cantidad_disponible: int
    factura_id: int


# ---------------------------------------------------------------------------
# Eventos de exportación
# ---------------------------------------------------------------------------

@dataclass
class PDFGenerado:
    factura_id: int
    ruta_archivo: str


@dataclass
class ImpresionSolicitada:
    factura_id: int
    impresora: Optional[str] = None   # None = impresora por defecto


# ---------------------------------------------------------------------------
# Eventos de sincronización con DuckDB remoto
# ---------------------------------------------------------------------------

@dataclass
class SincronizacionIniciada:
    desde: datetime
    hasta: datetime


@dataclass
class SincronizacionCompletada:
    registros_enviados: int
    duracion_segundos: float


@dataclass
class SincronizacionFallida:
    error: str
    reintentos: int
