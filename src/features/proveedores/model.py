"""
ProveedorModel

Reemplaza la lista en memoria por acceso a `catalogo.db` vía ProveedorRepository.
Mantiene la misma API de eventos (strings).
"""
from __future__ import annotations

from typing import Optional

from core.db.sqlite_manager import SqliteManager
from core.db.migrations_runner import DEFAULT_DB_PATHS
from events.proveedor_events import (
    Proveedor,
    CargarProveedoresRequestedEvent,
    GuardarProveedorRequestedEvent,
    EliminarProveedorRequestedEvent,
    ProveedoresCargadosEvent,
    ProveedorGuardadoEvent,
    ProveedorEliminadoEvent,
    ProveedorErrorEvent,
)
from features.proveedores.repository import ProveedorRepository


class ProveedorModel:
    """Gestiona los datos de proveedores persistidos en SQLite (catalogo.db)."""

    def __init__(
        self,
        event_bus,
        repository: Optional[ProveedorRepository] = None,
        db_path: Optional[str] = None,
        seed_si_vacio: bool = True,
    ):
        self.event_bus = event_bus
        if repository is not None:
            self._repo = repository
        else:
            path = db_path or DEFAULT_DB_PATHS["catalogo"]
            self._repo = ProveedorRepository(SqliteManager.get(path))

        if seed_si_vacio:
            self._repo.seed_si_vacio()

        self.event_bus.subscribe("cargar_proveedores_requested", self._handle_cargar)
        self.event_bus.subscribe("guardar_proveedor_requested", self._handle_guardar)
        self.event_bus.subscribe("eliminar_proveedor_requested", self._handle_eliminar)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _handle_cargar(self, event: CargarProveedoresRequestedEvent):
        try:
            proveedores = self._repo.listar()
            self.event_bus.emit(
                "proveedores_cargados",
                ProveedoresCargadosEvent(proveedores=proveedores),
            )
        except Exception as exc:
            self.event_bus.emit(
                "proveedor_error",
                ProveedorErrorEvent(f"Error al cargar proveedores: {exc}"),
            )

    def _handle_guardar(self, event: GuardarProveedorRequestedEvent):
        if not event.nombre.strip():
            self.event_bus.emit(
                "proveedor_error",
                ProveedorErrorEvent("El nombre del proveedor es obligatorio."),
            )
            return
        try:
            if event.proveedor_id is None:
                nuevo = self._repo.crear(
                    nombre=event.nombre.strip(),
                    contacto=event.contacto.strip(),
                    telefono=event.telefono.strip(),
                    email=event.email.strip(),
                    direccion=event.direccion.strip(),
                )
                self.event_bus.emit(
                    "proveedor_guardado",
                    ProveedorGuardadoEvent(proveedor=nuevo, es_nuevo=True),
                )
            else:
                actualizado: Optional[Proveedor] = self._repo.actualizar(
                    event.proveedor_id,
                    nombre=event.nombre.strip(),
                    contacto=event.contacto.strip(),
                    telefono=event.telefono.strip(),
                    email=event.email.strip(),
                    direccion=event.direccion.strip(),
                )
                if actualizado is None:
                    self.event_bus.emit(
                        "proveedor_error",
                        ProveedorErrorEvent(
                            f"No se encontró el proveedor con id={event.proveedor_id}."
                        ),
                    )
                    return
                self.event_bus.emit(
                    "proveedor_guardado",
                    ProveedorGuardadoEvent(proveedor=actualizado, es_nuevo=False),
                )
        except Exception as exc:
            self.event_bus.emit(
                "proveedor_error",
                ProveedorErrorEvent(f"Error al guardar proveedor: {exc}"),
            )

    def _handle_eliminar(self, event: EliminarProveedorRequestedEvent):
        try:
            ok = self._repo.eliminar(event.proveedor_id)
            if not ok:
                self.event_bus.emit(
                    "proveedor_error",
                    ProveedorErrorEvent(
                        f"No se encontró el proveedor con id={event.proveedor_id}."
                    ),
                )
                return
            self.event_bus.emit(
                "proveedor_eliminado",
                ProveedorEliminadoEvent(proveedor_id=event.proveedor_id),
            )
        except Exception as exc:
            self.event_bus.emit(
                "proveedor_error",
                ProveedorErrorEvent(f"Error al eliminar proveedor: {exc}"),
            )
