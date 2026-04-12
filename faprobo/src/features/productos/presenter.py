from core.base_presenter import BasePresenter


class ProductoPresenter(BasePresenter):
    """
    Coordinador MVP del módulo de Productos.
    Conecta el Model con la View a través del EventBus.
    """

    def _connect_events(self):
        # El Model ya se suscribe a sus propios eventos en su __init__.
        # El Presenter no necesita re-suscribirse a los mismos eventos.
        # Su rol principal es inicializar la carga de datos cuando
        # el presenter es instanciado.
        self._cargar_inicial()

    def _cargar_inicial(self):
        """Solicita la carga de productos al arrancar el módulo"""
        from events.producto_events import CargarProductosRequestedEvent
        self.event_bus.emit("cargar_productos_requested", CargarProductosRequestedEvent())
