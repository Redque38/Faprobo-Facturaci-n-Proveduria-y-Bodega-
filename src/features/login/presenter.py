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

        # Iniciar Módulo Facturación  (+ SyncService Fase 3)
        from core.db.sqlite_manager import SqliteManager
        from core.db.migrations_runner import DEFAULT_DB_PATHS
        from features.facturacion.model import FacturacionModel
        from features.facturacion.presenter import FacturacionPresenter
        from features.facturacion.repository import FacturaRepository

        fact_repo = FacturaRepository(SqliteManager.get(DEFAULT_DB_PATHS["facturas"]))
        fact_model = FacturacionModel(self.event_bus, repository=fact_repo)

        # SyncService: se crea perezosamente — si no hay MOTHERDUCK_TOKEN,
        # la app sigue funcionando y los pushes fallan con mensaje claro.
        try:
            from features.sync.sync_service import SyncService
            sync_svc = SyncService(self.event_bus, repository=fact_repo)
            fact_model.set_sync_service(sync_svc)
            fact_model.set_historial_downloader(sync_svc.como_downloader())
            self.sync_service = sync_svc  # mantener viva la referencia
        except Exception as exc:  # noqa: BLE001
            # No bloqueamos la UI si falta config; el usuario puede trabajar
            # en SQLite local y sincronizar cuando arregle el .env.
            import logging
            logging.getLogger(__name__).warning(
                "SyncService no disponible: %s", exc
            )

        FacturacionPresenter(fact_model, dashboard_view.page_facturacion, self.event_bus)

        # Iniciar Módulo Punto de Venta
        from features.punto_de_venta.model import PosModel
        from features.punto_de_venta.presenter import PosPresenter
        from features.punto_de_venta.repository import PosRepository
        pos_repo = PosRepository(SqliteManager.get(DEFAULT_DB_PATHS["catalogo"]))
        pos_model = PosModel(self.event_bus, pos_repo, fact_model)
        PosPresenter(pos_model, dashboard_view.page_pos, self.event_bus)

        # Iniciar Módulo Usuarios
        from features.usuarios.model import UsuariosModel
        from features.usuarios.presenter import UsuariosPresenter
        from features.usuarios.repository import UsuariosRepository
        usuarios_repo = UsuariosRepository(SqliteManager.get(DEFAULT_DB_PATHS["catalogo"]))
        UsuariosPresenter(
            UsuariosModel(self.event_bus, repository=usuarios_repo),
            dashboard_view.page_usuarios,
            self.event_bus,
        )

        # Nota: Referenciamos el window principal a nivel clase para evitar recolección de basura
        self.dashboard_view = dashboard_view
        self.dashboard_view.show()
        self.view.close()   # Cierra la ventana de login

    def handle_login_failed(self, event: LoginFailedEvent):
        self.view.show_error(event.message)