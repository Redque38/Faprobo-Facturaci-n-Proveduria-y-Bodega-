from dataclasses import dataclass
from typing import List


@dataclass
class Rol:
    id: int
    nombre: str
    descripcion: str
    activo: bool = True


@dataclass
class Usuario:
    id: int
    username: str
    nombre: str
    apellido: str
    rol_id: int
    rol_nombre: str
    activo: bool = True


# ── Solicitud ────────────────────────────────────────────────────────────────
@dataclass
class CargarUsuariosRequestedEvent:
    pass


@dataclass
class CargarRolesRequestedEvent:
    pass


@dataclass
class GuardarUsuarioRequestedEvent:
    usuario_id: int | None
    username: str
    nombre: str
    apellido: str
    password: str  # vacío = no cambia
    rol_id: int
    activo: bool


@dataclass
class EliminarUsuarioRequestedEvent:
    usuario_id: int


@dataclass
class GuardarRolRequestedEvent:
    rol_id: int | None
    nombre: str
    descripcion: str


@dataclass
class EliminarRolRequestedEvent:
    rol_id: int


# ── Respuesta ─────────────────────────────────────────────────────────────────
@dataclass
class UsuariosCargadosEvent:
    usuarios: List[Usuario]


@dataclass
class RolesCargadosEvent:
    roles: List[Rol]


@dataclass
class UsuarioGuardadoEvent:
    usuario: Usuario
    es_nuevo: bool


@dataclass
class UsuarioEliminadoEvent:
    usuario_id: int


@dataclass
class RolGuardadoEvent:
    rol: Rol
    es_nuevo: bool


@dataclass
class RolEliminadoEvent:
    rol_id: int


@dataclass
class UsuarioErrorEvent:
    mensaje: str


@dataclass
class UsuarioSincronizadoEvent:
    """Publicado después de crear/actualizar usuario o rol.
    El SyncService (Fase siguiente) capturará este evento para replicar a DuckDB."""
    entidad: str   # "usuario" | "rol"
    entidad_id: int
    operacion: str  # "crear" | "actualizar" | "eliminar"
