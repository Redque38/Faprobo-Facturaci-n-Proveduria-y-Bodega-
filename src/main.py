import sys
from PySide6.QtWidgets import QApplication, QMessageBox

from core import config
from core.db.migrations_runner import bootstrap_databases
from core.event_bus import EventBus
from features.login.model import LoginModel
from features.login.view import LoginView
from features.login.presenter import LoginPresenter


def main():
    app = QApplication(sys.argv)

    # 0) Cargar .env (MOTHERDUCK_TOKEN, SUCURSAL_ID, etc.).
    config.load()

    # 1) Asegurar que las bases de datos locales existen y están al día.
    try:
        bootstrap_databases(("facturas", "catalogo"))
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Error al inicializar bases de datos",
            f"No se pudo preparar la base local:\n{exc}",
        )
        sys.exit(1)

    event_bus = EventBus()

    model = LoginModel(event_bus)
    view = LoginView(event_bus)
    presenter = LoginPresenter(model, view, event_bus)  # noqa: F841

    view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
