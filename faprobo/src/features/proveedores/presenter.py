from core.base_presenter import BasePresenter


class ProveedorPresenter(BasePresenter):
    """
    Coordinador MVP del módulo de Proveedores.
    Conecta el Model con la View a través del EventBus.
    No contiene lógica de negocio ni lógica visual.
    """

    def _connect_events(self):
        # El Model ya se suscribe a sus propios eventos en su __init__.
        # El Presenter no necesita re-suscribirse a los mismos eventos.
        # Su rol principal es inicializar la carga de datos cuando
        # el presenter es instanciado.
        self._cargar_inicial()

    def _cargar_inicial(self):
        """Solicita la carga de proveedores al arrancar el módulo"""
        from events.proveedor_events import CargarProveedoresRequestedEvent
        self.event_bus.emit("cargar_proveedores_requested", CargarProveedoresRequestedEvent())
