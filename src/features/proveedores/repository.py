"""
ProveedorRepository: CRUD de proveedores sobre `catalogo.db`.
"""
from __future__ import annotations

from typing import Optional

from core.db.sqlite_manager import SqliteManager
from events.proveedor_events import Proveedor


class ProveedorRepository:
    def __init__(self, manager: SqliteManager):
        self._mgr = manager

    def seed_si_vacio(self) -> int:
        n = self._mgr.fetchone("SELECT COUNT(*) AS n FROM proveedores")["n"]
        if n > 0:
            return 0
        ejemplos = [
            ("TechComponents S.A.", "María García",    "8888-1111", "mgarcia@tech.com",   "San José, Local 4"),
            ("Distribuidora Norte", "Carlos Rodríguez", "8888-2222", "carlos@norte.com",   "Heredia, Centro"),
            ("Importaciones CR",    "Ana López",       "8888-3333", "ana@importcr.com",   "Alajuela, Zona Industrial"),
        ]
        with self._mgr.transaction() as conn:
            for nombre, contacto, tel, email, dir_ in ejemplos:
                conn.execute(
                    """
                    INSERT INTO proveedores (nombre, contacto, telefono, email, direccion)
                    VALUES (?,?,?,?,?)
                    """,
                    (nombre, contacto, tel, email, dir_),
                )
        return len(ejemplos)

    def listar(self, incluir_inactivos: bool = False) -> list[Proveedor]:
        q = "SELECT * FROM proveedores"
        if not incluir_inactivos:
            q += " WHERE activo = 1"
        q += " ORDER BY nombre"
        return [self._row_a_entidad(r) for r in self._mgr.fetchall(q)]

    def obtener(self, proveedor_id: int) -> Optional[Proveedor]:
        row = self._mgr.fetchone("SELECT * FROM proveedores WHERE id=?", (proveedor_id,))
        return self._row_a_entidad(row) if row else None

    def crear(
        self,
        *,
        nombre: str,
        contacto: str,
        telefono: str,
        email: str,
        direccion: str,
    ) -> Proveedor:
        with self._mgr.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO proveedores (nombre, contacto, telefono, email, direccion)
                VALUES (?,?,?,?,?)
                """,
                (nombre, contacto, telefono, email, direccion),
            )
            pid = cur.lastrowid
        creado = self.obtener(pid)
        assert creado is not None
        return creado

    def actualizar(
        self,
        proveedor_id: int,
        *,
        nombre: str,
        contacto: str,
        telefono: str,
        email: str,
        direccion: str,
    ) -> Optional[Proveedor]:
        cur = self._mgr.execute(
            """
            UPDATE proveedores
               SET nombre=?, contacto=?, telefono=?, email=?, direccion=?,
                   fecha_actualizacion=datetime('now')
             WHERE id=?
            """,
            (nombre, contacto, telefono, email, direccion, proveedor_id),
        )
        if cur.rowcount == 0:
            return None
        return self.obtener(proveedor_id)

    def eliminar(self, proveedor_id: int) -> bool:
        """Baja lógica."""
        cur = self._mgr.execute(
            "UPDATE proveedores SET activo=0, fecha_actualizacion=datetime('now') WHERE id=?",
            (proveedor_id,),
        )
        return cur.rowcount > 0

    def eliminar_duro(self, proveedor_id: int) -> bool:
        cur = self._mgr.execute("DELETE FROM proveedores WHERE id=?", (proveedor_id,))
        return cur.rowcount > 0

    @staticmethod
    def _row_a_entidad(row) -> Proveedor:
        return Proveedor(
            id=row["id"],
            nombre=row["nombre"],
            contacto=row["contacto"],
            telefono=row["telefono"],
            email=row["email"],
            direccion=row["direccion"],
        )
