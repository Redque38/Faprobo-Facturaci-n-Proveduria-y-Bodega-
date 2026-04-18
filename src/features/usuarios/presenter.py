from core.base_presenter import BasePresenter


class UsuariosPresenter(BasePresenter):
    """
    Coordinador MVP del módulo de Usuarios & Roles.
    El Model y la View se suscriben a sus propios eventos en sus __init__.
    El Presenter solo dispara la carga inicial.
    """

    def _connect_events(self) -> None:
        self._cargar_inicial()

    def _cargar_inicial(self) -> None:
        from events.usuario_events import (
            CargarUsuariosRequestedEvent,
            CargarRolesRequestedEvent,
        )
        self.event_bus.emit("cargar_usuarios_requested", CargarUsuariosRequestedEvent())
        self.event_bus.emit("cargar_roles_requested",    CargarRolesRequestedEvent())
