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


class ProductoModel:
    """
    Gestiona los datos de productos.
    Por ahora usa una lista en memoria con datos de ejemplo.
    Al implementar una DB, solo se modifica este archivo.
    """

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._productos: list[Producto] = []
        self._next_id: int = 1
        self._seed_data()

        # Suscribirse a solicitudes
        self.event_bus.subscribe("cargar_productos_requested", self._handle_cargar)
        self.event_bus.subscribe("guardar_producto_requested", self._handle_guardar)
        self.event_bus.subscribe("eliminar_producto_requested", self._handle_eliminar)

    # ──────────────────────────────────────────────
    # Datos de ejemplo para desarrollo
    # ──────────────────────────────────────────────

    def _seed_data(self):
        ejemplos = [
            ("P001", "Laptop Dell XPS 13", "Laptop ultra portátil de 13 pulgadas", 800.0, 1200.0, 15, "Electrónica"),
            ("P002", "Monitor LG 27'", "Monitor 4K IPS", 250.0, 350.0, 30, "Monitores"),
            ("P003", "Teclado Mecánico Keychron", "Teclado mecánico Bluetooth", 60.0, 100.0, 50, "Periféricos"),
        ]
        for codigo, nombre, descripcion, p_compra, p_venta, stock, categoria in ejemplos:
            self._productos.append(
                Producto(
                    id=self._next_id,
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=descripcion,
                    precio_compra=p_compra,
                    precio_venta=p_venta,
                    stock=stock,
                    categoria=categoria,
                )
            )
            self._next_id += 1

    # ──────────────────────────────────────────────
    # Handlers
    # ──────────────────────────────────────────────

    def _handle_cargar(self, event: CargarProductosRequestedEvent):
        self.event_bus.emit(
            "productos_cargados",
            ProductosCargadosEvent(productos=list(self._productos)),
        )

    def _handle_guardar(self, event: GuardarProductoRequestedEvent):
        # Validación básica
        if not event.codigo.strip() or not event.nombre.strip():
            self.event_bus.emit(
                "producto_error",
                ProductoErrorEvent("El código y el nombre del producto son obligatorios."),
            )
            return

        if event.producto_id is None:
            # Nuevo producto
            nuevo = Producto(
                id=self._next_id,
                codigo=event.codigo.strip(),
                nombre=event.nombre.strip(),
                descripcion=event.descripcion.strip(),
                precio_compra=event.precio_compra,
                precio_venta=event.precio_venta,
                stock=event.stock,
                categoria=event.categoria.strip(),
            )
            self._productos.append(nuevo)
            self._next_id += 1
            self.event_bus.emit(
                "producto_guardado",
                ProductoGuardadoEvent(producto=nuevo, es_nuevo=True),
            )
        else:
            # Edición
            for i, p in enumerate(self._productos):
                if p.id == event.producto_id:
                    actualizado = Producto(
                        id=p.id,
                        codigo=event.codigo.strip(),
                        nombre=event.nombre.strip(),
                        descripcion=event.descripcion.strip(),
                        precio_compra=event.precio_compra,
                        precio_venta=event.precio_venta,
                        stock=event.stock,
                        categoria=event.categoria.strip(),
                    )
                    self._productos[i] = actualizado
                    self.event_bus.emit(
                        "producto_guardado",
                        ProductoGuardadoEvent(producto=actualizado, es_nuevo=False),
                    )
                    return
            self.event_bus.emit(
                "producto_error",
                ProductoErrorEvent(f"No se encontró el producto con id={event.producto_id}."),
            )

    def _handle_eliminar(self, event: EliminarProductoRequestedEvent):
        for i, p in enumerate(self._productos):
            if p.id == event.producto_id:
                self._productos.pop(i)
                self.event_bus.emit(
                    "producto_eliminado",
                    ProductoEliminadoEvent(producto_id=event.producto_id),
                )
                return
        self.event_bus.emit(
            "producto_error",
            ProductoErrorEvent(f"No se encontró el producto con id={event.producto_id}."),
        )
