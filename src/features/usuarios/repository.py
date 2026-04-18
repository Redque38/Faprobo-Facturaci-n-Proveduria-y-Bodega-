"""
UsuariosRepository

Acceso a las tablas `usuarios` y `roles` en catalogo.db.
Todas las operaciones de borrado son lógicas (activo = 0).
"""
from __future__ import annotations

import hashlib
from typing import Optional

from core.db.sqlite_manager import SqliteManager
from events.usuario_events import Rol, Usuario


class UsuariosRepository:
    def __init__(self, db: SqliteManager):
        self._db = db

    # ── Utilidades ───────────────────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        """Devuelve el hash SHA-256 hex del password en texto plano."""
        return hashlib.sha256(password.encode()).hexdigest()

    # ── Roles ─────────────────────────────────────────────────────────────────

    def listar_roles(self) -> list[dict]:
        rows = self._db.fetchall(
            "SELECT id, nombre, descripcion, activo FROM roles WHERE activo = 1 ORDER BY nombre"
        )
        return [dict(r) for r in rows]

    def crear_rol(self, nombre: str, descripcion: str) -> int:
        self._db.execute(
            "INSERT INTO roles (nombre, descripcion) VALUES (?, ?)",
            (nombre, descripcion),
        )
        row = self._db.fetchone("SELECT last_insert_rowid() AS id")
        return int(row["id"])

    def actualizar_rol(self, id: int, nombre: str, descripcion: str) -> None:
        self._db.execute(
            "UPDATE roles SET nombre = ?, descripcion = ? WHERE id = ?",
            (nombre, descripcion, id),
        )

    def eliminar_rol(self, id: int) -> None:
        """Borrado lógico."""
        self._db.execute("UPDATE roles SET activo = 0 WHERE id = ?", (id,))

    def contar_usuarios_por_rol(self, rol_id: int) -> int:
        row = self._db.fetchone(
            "SELECT COUNT(*) AS cnt FROM usuarios WHERE rol_id = ? AND activo = 1",
            (rol_id,),
        )
        return int(row["cnt"]) if row else 0

    # ── Usuarios ──────────────────────────────────────────────────────────────

    def listar_usuarios(self) -> list[dict]:
        rows = self._db.fetchall(
            """
            SELECT u.id, u.username, u.nombre, u.apellido,
                   u.rol_id, r.nombre AS rol_nombre, u.activo
            FROM usuarios u
            JOIN roles r ON r.id = u.rol_id
            WHERE u.activo = 1
            ORDER BY u.nombre
            """
        )
        return [dict(r) for r in rows]

    def crear_usuario(
        self,
        username: str,
        nombre: str,
        apellido: str,
        password_hash: str,
        rol_id: int,
    ) -> int:
        self._db.execute(
            """
            INSERT INTO usuarios (username, nombre, apellido, password_hash, rol_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, nombre, apellido, password_hash, rol_id),
        )
        row = self._db.fetchone("SELECT last_insert_rowid() AS id")
        return int(row["id"])

    def actualizar_usuario(
        self,
        id: int,
        username: str,
        nombre: str,
        apellido: str,
        password_hash: Optional[str],
        rol_id: int,
        activo: bool,
    ) -> None:
        if password_hash:
            self._db.execute(
                """
                UPDATE usuarios
                SET username = ?, nombre = ?, apellido = ?,
                    password_hash = ?, rol_id = ?, activo = ?,
                    fecha_actualizacion = datetime('now')
                WHERE id = ?
                """,
                (username, nombre, apellido, password_hash, rol_id, int(activo), id),
            )
        else:
            self._db.execute(
                """
                UPDATE usuarios
                SET username = ?, nombre = ?, apellido = ?,
                    rol_id = ?, activo = ?,
                    fecha_actualizacion = datetime('now')
                WHERE id = ?
                """,
                (username, nombre, apellido, rol_id, int(activo), id),
            )

    def eliminar_usuario(self, id: int) -> None:
        """Borrado lógico."""
        self._db.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (id,))
