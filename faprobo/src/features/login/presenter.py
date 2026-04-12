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

        dashboard_view.show()
        self.view.close()   # Cierra la ventana de login

    def handle_login_failed(self, event: LoginFailedEvent):
        self.view.show_error(event.message)