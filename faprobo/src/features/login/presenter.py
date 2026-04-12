from core.base_presenter import BasePresenter
from events.login_events import LoginRequestedEvent, LoginSuccessEvent, LoginFailedEvent

class LoginPresenter(BasePresenter):
    def _connect_events(self):
        self.event_bus.subscribe("login_requested", self.handle_login_requested)
        self.event_bus.subscribe("login_success", self.handle_login_success)
        self.event_bus.subscribe("login_failed", self.handle_login_failed)

    def handle_login_requested(self, event: LoginRequestedEvent):
        self.model.authenticate(event.username, event.password)

    def handle_login_success(self, event: LoginSuccessEvent):
        self.view.show_success(event.username)
    
        # Abrir Dashboard
        from features.dashboard.view import DashboardView
        from features.dashboard.model import DashboardModel   # lo crearemos después
        from features.dashboard.presenter import DashboardPresenter

        dashboard_model = DashboardModel(self.event_bus)
        dashboard_view = DashboardView(self.event_bus)
        DashboardPresenter(dashboard_model, dashboard_view, self.event_bus)

        # Iniciar Módulo Proveedores
        from features.proveedores.model import ProveedorModel
        from features.proveedores.presenter import ProveedorPresenter
        ProveedorPresenter(ProveedorModel(self.event_bus), dashboard_view.page_proveedores, self.event_bus)

        # Iniciar Módulo Productos
        from features.productos.model import ProductoModel
        from features.productos.presenter import ProductoPresenter
        ProductoPresenter(ProductoModel(self.event_bus), dashboard_view.page_productos, self.event_bus)

        # Nota: Referenciamos el window principal a nivel clase para evitar recolección de basura
        self.dashboard_view = dashboard_view
        self.dashboard_view.show()
        self.view.close()   # Cierra la ventana de login

    def handle_login_failed(self, event: LoginFailedEvent):
        self.view.show_error(event.message)