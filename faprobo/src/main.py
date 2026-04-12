import sys
from PySide6.QtWidgets import QApplication

from core.event_bus import EventBus
#from features.login.model import LoginModel
from features.login.view import LoginView
#from features.login.presenter import LoginPresenter

def main():
    app = QApplication(sys.argv)
    
    event_bus = EventBus()

    # Crear las tres partes del MVP
    # model = LoginModel(event_bus)
    view = LoginView(event_bus)
    #presenter = LoginPresenter(model, view, event_bus)

    view.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()