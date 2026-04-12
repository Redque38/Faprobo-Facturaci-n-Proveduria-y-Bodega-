from dataclasses import dataclass, field
from typing import List


@dataclass
class Proveedor:
    """Entidad principal del módulo de Proveedores"""
    id: int
    nombre: str
    contacto: str
    telefono: str
    email: str
    direccion: str


# ──── Eventos de solicitud (View → Presenter → Model) ────────────────────────

@dataclass
class CargarProveedoresRequestedEvent:
    """Se emite cuando la vista quiere cargar la lista de proveedores"""
    pass


@dataclass
class GuardarProveedorRequestedEvent:
    """Se emite al enviar el formulario de nuevo proveedor o edición"""
    proveedor_id: int | None   # None = nuevo, int = edición
    nombre: str
    contacto: str
    telefono: str
    email: str
    direccion: str


@dataclass
class EliminarProveedorRequestedEvent:
    """Se emite al hacer clic en Eliminar"""
    proveedor_id: int


# ──── Eventos de respuesta (Model → Presenter → View) ────────────────────────

@dataclass
class ProveedoresCargadosEvent:
    """El model responde con la lista completa"""
    proveedores: List[Proveedor]


@dataclass
class ProveedorGuardadoEvent:
    """El proveedor fue guardado (nuevo o actualizado)"""
    proveedor: Proveedor
    es_nuevo: bool


@dataclass
class ProveedorEliminadoEvent:
    """El proveedor fue eliminado"""
    proveedor_id: int


@dataclass
class ProveedorErrorEvent:
    """Ocurrió un error en cualquier operación"""
    mensaje: str
