from dataclasses import dataclass

@dataclass
class LoginRequestedEvent:
    username: str
    password: str

@dataclass
class LoginSuccessEvent:
    username: str

@dataclass
class LoginFailedEvent:
    message: str