from events.login_events import LoginSuccessEvent, LoginFailedEvent

class LoginModel:
    def __init__(self, event_bus):
        self.event_bus = event_bus

    def authenticate(self, username: str, password: str):
        # Simulación por ahora (después conectarás con tu base de datos o API)
        if username.strip() and password.strip():   # ejemplo simple
            # En un caso real: consulta a DB o servicio
            if username == "admin" and password == "123":
                self.event_bus.emit("login_success", LoginSuccessEvent(username))
            else:
                self.event_bus.emit("login_failed", LoginFailedEvent("Usuario o contraseña incorrectos"))
        else:
            self.event_bus.emit("login_failed", LoginFailedEvent("Completa todos los campos"))