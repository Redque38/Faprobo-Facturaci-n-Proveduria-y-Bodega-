"""
ProductoModel

Reemplaza la lista en memoria por acceso a `catalogo.db` vía ProductoRepository.
Mantiene la misma API de eventos (strings) ya consumida por el presenter.
"""
from __future__ import annotations

from typing import Optional

from core.db.sqlite_manager import SqliteManager
from core.db.migrations_runner import DEFAULT_DB_PATHS
from events.producto_events import (
    Producto,
    CargarProductosRequestedEvent,
    GuardarProductoRequestedEvent,
    EliminarProductoRequestedEvent,
    ProductosCargadosEvent,
    ProductoGuardadoEvent,
    ProductoEliminadoEvent,
    ProductoErrorEvent,
)
from events.facturacion_events import StockSolicitado, StockDescontado, StockInsuficiente
from features.productos.repository import ProductoRepository


class ProductoModel:
    """Gestiona los datos de productos persistidos en SQLite (catalogo.db)."""

    def __init__(
        self,
        event_bus,
        repository: Optional[ProductoRepository] = None,
        db_path: Optional[str] = None,
        seed_si_vacio: bool = True,
    ):
        self.event_bus = event_bus
        if repository is not None:
            self._repo = repository
        else:
            path = db_path or DEFAULT_DB_PATHS["catalogo"]
            self._repo = ProductoRepository(SqliteManager.get(path))

        if seed_si_vacio:
            self._repo.seed_si_vacio()

        self.event_bus.subscribe("cargar_productos_requested", self._handle_cargar)
        self.event_bus.subscribe("guardar_producto_requested", self._handle_guardar)
        self.event_bus.subscribe("eliminar_producto_requested", self._handle_eliminar)
        # Bodega: descuenta stock cuando Facturación crea una venta
        self.event_bus.subscribe(StockSolicitado, self._handle_stock_solicitado)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _handle_cargar(self, event: CargarProductosRequestedEvent):
        try:
            productos = self._repo.listar()
            self.event_bus.emit(
                "productos_cargados",
                ProductosCargadosEvent(productos=productos),
            )
        except Exception as exc:
            self.event_bus.emit(
                "producto_error",
                ProductoErrorEvent(f"Error al cargar productos: {exc}"),
            )

    def _handle_guardar(self, event: GuardarProductoRequestedEvent):
        if not event.codigo.strip() or not event.nombre.strip():
            self.event_bus.emit(
                "producto_error",
                ProductoErrorEvent("El código y el nombre del producto son obligatorios."),
            )
            return

        try:
            if event.producto_id is None:
                # Guarda: detectar colisión de código antes de insertar
                if self._repo.obtener_por_codigo(event.codigo.strip()) is not None:
                    self.event_bus.emit(
                        "producto_error",
                        ProductoErrorEvent(
                            f"Ya existe un producto con el código '{event.codigo.strip()}'."
                        ),
                    )
                    return
                nuevo = self._repo.crear(
                    codigo=event.codigo.strip(),
                    nombre=event.nombre.strip(),
                    descripcion=event.descripcion.strip(),
                    precio_compra=event.precio_compra,
                    precio_venta=event.precio_venta,
                    stock=event.stock,
                    categoria=event.categoria.strip(),
                )
                self.event_bus.emit(
                    "producto_guardado",
                    ProductoGuardadoEvent(producto=nuevo, es_nuevo=True),
                )
            else:
                actualizado: Optional[Producto] = self._repo.actualizar(
                    event.producto_id,
                    codigo=event.codigo.strip(),
                    nombre=event.nombre.strip(),
                    descripcion=event.descripcion.strip(),
                    precio_compra=event.precio_compra,
                    precio_venta=event.precio_venta,
                    stock=event.stock,
                    categoria=event.categoria.strip(),
                )
                if actualizado is None:
                    self.event_bus.emit(
                        "producto_error",
                        ProductoErrorEvent(
                            f"No se encontró el producto con id={event.producto_id}."
                        ),
                    )
                    return
                self.event_bus.emit(
                    "producto_guardado",
                    ProductoGuardadoEvent(producto=actualizado, es_nuevo=False),
                )
        except Exception as exc:
            self.event_bus.emit(
                "producto_error",
                ProductoErrorEvent(f"Error al guardar producto: {exc}"),
            )

    def _handle_eliminar(self, event: EliminarProductoRequestedEvent):
        try:
            ok = self._repo.eliminar(event.producto_id)
            if not ok:
                self.event_bus.emit(
                    "producto_error",
                    ProductoErrorEvent(
                        f"No se encontró el producto con id={event.producto_id}."
                    ),
                )
                return
            self.event_bus.emit(
                "producto_eliminado",
                ProductoEliminadoEvent(producto_id=event.producto_id),
            )
        except Exception as exc:
            self.event_bus.emit(
                "producto_error",
                ProductoErrorEvent(f"Error al eliminar producto: {exc}"),
            )

    def _handle_stock_solicitado(self, event: StockSolicitado) -> None:
        """
        Descuenta stock cuando Facturación crea una venta.
        Publica StockDescontado si hay suficiente stock, StockInsuficiente si no.
        """
        try:
            producto = self._repo.obtener(event.producto_id)
            if producto is None:
                # Producto no existe — publicar insuficiente para que la factura se anule
                self.event_bus.publish(StockInsuficiente(
                    producto_id=event.producto_id,
                    cantidad_solicitada=event.cantidad,
                    cantidad_disponible=0,
                    factura_id=event.factura_id,
                ))
                return

            if producto.stock < event.cantidad:
                self.event_bus.publish(StockInsuficiente(
                    producto_id=event.producto_id,
                    cantidad_solicitada=event.cantidad,
                    cantidad_disponible=producto.stock,
                    factura_id=event.factura_id,
                ))
                return

            stock_nuevo = self._repo.actualizar_stock(event.producto_id, -event.cantidad)
            self.event_bus.publish(StockDescontado(
                producto_id=event.producto_id,
                cantidad=event.cantidad,
                factura_id=event.factura_id,
                stock_restante=stock_nuevo if stock_nuevo is not None else 0,
            ))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "Error al descontar stock producto_id=%s: %s", event.producto_id, exc
            )
