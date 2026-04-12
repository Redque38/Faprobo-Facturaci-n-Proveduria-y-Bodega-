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


class ProveedorModel:
    """
    Gestiona los datos de proveedores.
    Por ahora usa una lista en memoria con datos de ejemplo.
    Al implementar una DB, solo se modifica este archivo.
    """

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._proveedores: list[Proveedor] = []
        self._next_id: int = 1
        self._seed_data()

        # Suscribirse a solicitudes
        self.event_bus.subscribe("cargar_proveedores_requested", self._handle_cargar)
        self.event_bus.subscribe("guardar_proveedor_requested", self._handle_guardar)
        self.event_bus.subscribe("eliminar_proveedor_requested", self._handle_eliminar)

    # ──────────────────────────────────────────────
    # Datos de ejemplo para desarrollo
    # ──────────────────────────────────────────────

    def _seed_data(self):
        ejemplos = [
            ("TechComponents S.A.", "María García",    "8888-1111", "mgarcia@tech.com",    "San José, Local 4"),
            ("Distribuidora Norte", "Carlos Rodríguez","8888-2222", "carlos@norte.com",    "Heredia, Centro"),
            ("Importaciones CR",   "Ana López",        "8888-3333", "ana@importcr.com",    "Alajuela, Zona Industrial"),
        ]
        for nombre, contacto, tel, email, dir_ in ejemplos:
            self._proveedores.append(
                Proveedor(
                    id=self._next_id,
                    nombre=nombre,
                    contacto=contacto,
                    telefono=tel,
                    email=email,
                    direccion=dir_,
                )
            )
            self._next_id += 1

    # ──────────────────────────────────────────────
    # Handlers
    # ──────────────────────────────────────────────

    def _handle_cargar(self, event: CargarProveedoresRequestedEvent):
        self.event_bus.emit(
            "proveedores_cargados",
            ProveedoresCargadosEvent(proveedores=list(self._proveedores)),
        )

    def _handle_guardar(self, event: GuardarProveedorRequestedEvent):
        # Validación básica
        if not event.nombre.strip():
            self.event_bus.emit(
                "proveedor_error",
                ProveedorErrorEvent("El nombre del proveedor es obligatorio."),
            )
            return

        if event.proveedor_id is None:
            # Nuevo proveedor
            nuevo = Proveedor(
                id=self._next_id,
                nombre=event.nombre.strip(),
                contacto=event.contacto.strip(),
                telefono=event.telefono.strip(),
                email=event.email.strip(),
                direccion=event.direccion.strip(),
            )
            self._proveedores.append(nuevo)
            self._next_id += 1
            self.event_bus.emit(
                "proveedor_guardado",
                ProveedorGuardadoEvent(proveedor=nuevo, es_nuevo=True),
            )
        else:
            # Edición
            for i, p in enumerate(self._proveedores):
                if p.id == event.proveedor_id:
                    actualizado = Proveedor(
                        id=p.id,
                        nombre=event.nombre.strip(),
                        contacto=event.contacto.strip(),
                        telefono=event.telefono.strip(),
                        email=event.email.strip(),
                        direccion=event.direccion.strip(),
                    )
                    self._proveedores[i] = actualizado
                    self.event_bus.emit(
                        "proveedor_guardado",
                        ProveedorGuardadoEvent(proveedor=actualizado, es_nuevo=False),
                    )
                    return
            self.event_bus.emit(
                "proveedor_error",
                ProveedorErrorEvent(f"No se encontró el proveedor con id={event.proveedor_id}."),
            )

    def _handle_eliminar(self, event: EliminarProveedorRequestedEvent):
        for i, p in enumerate(self._proveedores):
            if p.id == event.proveedor_id:
                self._proveedores.pop(i)
                self.event_bus.emit(
                    "proveedor_eliminado",
                    ProveedorEliminadoEvent(proveedor_id=event.proveedor_id),
                )
                return
        self.event_bus.emit(
            "proveedor_error",
            ProveedorErrorEvent(f"No se encontró el proveedor con id={event.proveedor_id}."),
        )
