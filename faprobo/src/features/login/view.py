from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QPushButton, 
                               QLabel, QMessageBox, QFormLayout)
from PySide6.QtCore import Qt

from events.login_events import LoginRequestedEvent

class LoginView(QWidget):
    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus

        self.setWindowTitle("Faprobo - Iniciar Sesión")
        self.setFixedSize(380, 280)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 30, 40, 30)

        title = QLabel("Iniciar Sesión")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Usuario")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form_layout.addRow("Usuario:", self.username_input)
        form_layout.addRow("Contraseña:", self.password_input)

        self.btn_login = QPushButton("Ingresar")
        self.btn_login.setDefault(True)

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.btn_login)
        layout.addStretch()

        self.setLayout(layout)

        # Conectar botón → evento
        self.btn_login.clicked.connect(self._emit_login_requested)

    def _emit_login_requested(self):
        event = LoginRequestedEvent(
            username=self.username_input.text().strip(),
            password=self.password_input.text().strip()
        )
        self.event_bus.emit("login_requested", event)

    def show_error(self, message: str):
        QMessageBox.warning(self, "Error de Login", message)

    def show_success(self, username: str):
        QMessageBox.information(self, "Éxito", f"¡Bienvenido {username}!")