"""
UsuariosModel

Gestiona usuarios y roles en catalogo.db.
Publica UsuarioSincronizadoEvent para que la Fase siguiente conecte DuckDB.
"""
from __future__ import annotations

import logging
from typing import Optional

from core.db.sqlite_manager import SqliteManager
from core.db.migrations_runner import DEFAULT_DB_PATHS
from events.usuario_events import (
    Rol,
    Usuario,
    CargarUsuariosRequestedEvent,
    CargarRolesRequestedEvent,
    GuardarUsuarioRequestedEvent,
    EliminarUsuarioRequestedEvent,
    GuardarRolRequestedEvent,
    EliminarRolRequestedEvent,
    UsuariosCargadosEvent,
    RolesCargadosEvent,
    UsuarioGuardadoEvent,
    UsuarioEliminadoEvent,
    RolGuardadoEvent,
    RolEliminadoEvent,
    UsuarioErrorEvent,
    UsuarioSincronizadoEvent,
)
from features.usuarios.repository import UsuariosRepository

_log = logging.getLogger(__name__)


class UsuariosModel:
    def __init__(
        self,
        event_bus,
        repository: Optional[UsuariosRepository] = None,
        db_path: Optional[str] = None,
    ):
        self.event_bus = event_bus
        if repository is not None:
            self._repo = repository
        else:
            path = db_path or DEFAULT_DB_PATHS["catalogo"]
            self._repo = UsuariosRepository(SqliteManager.get(path))

        # Suscripciones
        self.event_bus.subscribe("cargar_usuarios_requested",  self._handle_cargar_usuarios)
        self.event_bus.subscribe("cargar_roles_requested",     self._handle_cargar_roles)
        self.event_bus.subscribe("guardar_usuario_requested",  self._handle_guardar_usuario)
        self.event_bus.subscribe("eliminar_usuario_requested", self._handle_eliminar_usuario)
        self.event_bus.subscribe("guardar_rol_requested",      self._handle_guardar_rol)
        self.event_bus.subscribe("eliminar_rol_requested",     self._handle_eliminar_rol)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _dict_a_usuario(self, d: dict) -> Usuario:
        return Usuario(
            id=d["id"],
            username=d["username"],
            nombre=d["nombre"],
            apellido=d["apellido"],
            rol_id=d["rol_id"],
            rol_nombre=d["rol_nombre"],
            activo=bool(d["activo"]),
        )

    def _dict_a_rol(self, d: dict) -> Rol:
        return Rol(
            id=d["id"],
            nombre=d["nombre"],
            descripcion=d["descripcion"],
            activo=bool(d["activo"]),
        )

    def _publicar_sync(self, entidad: str, entidad_id: int, operacion: str) -> None:
        """Stub de sincronización con DuckDB — pendiente de implementar en Fase siguiente."""
        _log.info(
            "UsuarioSincronizadoEvent pendiente de sync a DuckDB: "
            "entidad=%s id=%s operacion=%s",
            entidad,
            entidad_id,
            operacion,
        )
        self.event_bus.emit(
            "usuario_sincronizado",
            UsuarioSincronizadoEvent(
                entidad=entidad, entidad_id=entidad_id, operacion=operacion
            ),
        )

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _handle_cargar_usuarios(self, _event: CargarUsuariosRequestedEvent):
        try:
            rows = self._repo.listar_usuarios()
            usuarios = [self._dict_a_usuario(r) for r in rows]
            self.event_bus.emit("usuarios_cargados", UsuariosCargadosEvent(usuarios=usuarios))
        except Exception as exc:
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje=f"Error al cargar usuarios: {exc}"))

    def _handle_cargar_roles(self, _event: CargarRolesRequestedEvent):
        try:
            rows = self._repo.listar_roles()
            roles = [self._dict_a_rol(r) for r in rows]
            self.event_bus.emit("roles_cargados", RolesCargadosEvent(roles=roles))
        except Exception as exc:
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje=f"Error al cargar roles: {exc}"))

    def _handle_guardar_usuario(self, event: GuardarUsuarioRequestedEvent):
        if not event.username.strip():
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje="El username es obligatorio."))
            return
        if not event.nombre.strip():
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje="El nombre es obligatorio."))
            return
        try:
            password_hash: Optional[str] = None
            if event.password:
                password_hash = self._repo.hash_password(event.password)

            if event.usuario_id is None:
                if not event.password:
                    self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje="La contraseña es obligatoria para nuevos usuarios."))
                    return
                nuevo_id = self._repo.crear_usuario(
                    username=event.username.strip(),
                    nombre=event.nombre.strip(),
                    apellido=event.apellido.strip(),
                    password_hash=password_hash,
                    rol_id=event.rol_id,
                )
                rows = self._repo.listar_usuarios()
                usuario = next(
                    (self._dict_a_usuario(r) for r in rows if r["id"] == nuevo_id),
                    None,
                )
                if usuario is None:
                    raise RuntimeError(f"No se encontró usuario recién creado id={nuevo_id}")
                self.event_bus.emit("usuario_guardado", UsuarioGuardadoEvent(usuario=usuario, es_nuevo=True))
                self._publicar_sync("usuario", nuevo_id, "crear")
            else:
                self._repo.actualizar_usuario(
                    id=event.usuario_id,
                    username=event.username.strip(),
                    nombre=event.nombre.strip(),
                    apellido=event.apellido.strip(),
                    password_hash=password_hash,
                    rol_id=event.rol_id,
                    activo=event.activo,
                )
                rows = self._repo.listar_usuarios()
                usuario = next(
                    (self._dict_a_usuario(r) for r in rows if r["id"] == event.usuario_id),
                    None,
                )
                if usuario is None:
                    # El usuario puede estar inactivo ahora; construir uno mínimo
                    usuario = Usuario(
                        id=event.usuario_id,
                        username=event.username,
                        nombre=event.nombre,
                        apellido=event.apellido,
                        rol_id=event.rol_id,
                        rol_nombre="",
                        activo=event.activo,
                    )
                self.event_bus.emit("usuario_guardado", UsuarioGuardadoEvent(usuario=usuario, es_nuevo=False))
                self._publicar_sync("usuario", event.usuario_id, "actualizar")
        except Exception as exc:
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje=f"Error al guardar usuario: {exc}"))

    def _handle_eliminar_usuario(self, event: EliminarUsuarioRequestedEvent):
        try:
            self._repo.eliminar_usuario(event.usuario_id)
            self.event_bus.emit("usuario_eliminado", UsuarioEliminadoEvent(usuario_id=event.usuario_id))
            self._publicar_sync("usuario", event.usuario_id, "eliminar")
        except Exception as exc:
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje=f"Error al eliminar usuario: {exc}"))

    def _handle_guardar_rol(self, event: GuardarRolRequestedEvent):
        if not event.nombre.strip():
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje="El nombre del rol es obligatorio."))
            return
        try:
            if event.rol_id is None:
                nuevo_id = self._repo.crear_rol(
                    nombre=event.nombre.strip(),
                    descripcion=event.descripcion.strip(),
                )
                rows = self._repo.listar_roles()
                rol = next(
                    (self._dict_a_rol(r) for r in rows if r["id"] == nuevo_id),
                    None,
                )
                if rol is None:
                    raise RuntimeError(f"No se encontró rol recién creado id={nuevo_id}")
                self.event_bus.emit("rol_guardado", RolGuardadoEvent(rol=rol, es_nuevo=True))
                self._publicar_sync("rol", nuevo_id, "crear")
            else:
                self._repo.actualizar_rol(
                    id=event.rol_id,
                    nombre=event.nombre.strip(),
                    descripcion=event.descripcion.strip(),
                )
                rol = Rol(
                    id=event.rol_id,
                    nombre=event.nombre.strip(),
                    descripcion=event.descripcion.strip(),
                )
                self.event_bus.emit("rol_guardado", RolGuardadoEvent(rol=rol, es_nuevo=False))
                self._publicar_sync("rol", event.rol_id, "actualizar")
        except Exception as exc:
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje=f"Error al guardar rol: {exc}"))

    def _handle_eliminar_rol(self, event: EliminarRolRequestedEvent):
        try:
            en_uso = self._repo.contar_usuarios_por_rol(event.rol_id)
            if en_uso > 0:
                self.event_bus.emit(
                    "usuario_error",
                    UsuarioErrorEvent(
                        mensaje=f"No se puede eliminar el rol: tiene {en_uso} usuario(s) activo(s)."
                    ),
                )
                return
            self._repo.eliminar_rol(event.rol_id)
            self.event_bus.emit("rol_eliminado", RolEliminadoEvent(rol_id=event.rol_id))
            self._publicar_sync("rol", event.rol_id, "eliminar")
        except Exception as exc:
            self.event_bus.emit("usuario_error", UsuarioErrorEvent(mensaje=f"Error al eliminar rol: {exc}"))
