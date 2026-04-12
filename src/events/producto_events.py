from dataclasses import dataclass
from typing import List


@dataclass
class Producto:
    """Entidad principal del módulo de Productos"""
    id: int
    codigo: str
    nombre: str
    descripcion: str
    precio_compra: float
    precio_venta: float
    stock: int
    categoria: str


# ──── Eventos de solicitud (View → Presenter → Model) ────────────────────────

@dataclass
class CargarProductosRequestedEvent:
    """Se emite cuando la vista quiere cargar la lista de productos"""
    pass


@dataclass
class GuardarProductoRequestedEvent:
    """Se emite al enviar el formulario de nuevo producto o edición"""
    producto_id: int | None   # None = nuevo, int = edición
    codigo: str
    nombre: str
    descripcion: str
    precio_compra: float
    precio_venta: float
    stock: int
    categoria: str


@dataclass
class EliminarProductoRequestedEvent:
    """Se emite al hacer clic en Eliminar"""
    producto_id: int


# ──── Eventos de respuesta (Model → Presenter → View) ────────────────────────

@dataclass
class ProductosCargadosEvent:
    """El model responde con la lista completa de productos"""
    productos: List[Producto]


@dataclass
class ProductoGuardadoEvent:
    """El producto fue guardado (nuevo o actualizado)"""
    producto: Producto
    es_nuevo: bool


@dataclass
class ProductoEliminadoEvent:
    """El producto fue eliminado"""
    producto_id: int


@dataclass
class ProductoErrorEvent:
    """Ocurrió un error en cualquier operación de producto"""
    mensaje: str
