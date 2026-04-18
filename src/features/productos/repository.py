"""
ProductoRepository: CRUD de productos sobre `catalogo.db`.
Devuelve dataclasses Producto ya definidos en events.producto_events.
"""
from __future__ import annotations

from typing import Optional

from core.db.sqlite_manager import SqliteManager
from events.producto_events import Producto


class ProductoRepository:
    def __init__(self, manager: SqliteManager):
        self._mgr = manager

    # ------------------------------------------------------------------
    # Seed opcional (para arrancar con datos de ejemplo si la tabla está vacía)
    # ------------------------------------------------------------------
    def seed_si_vacio(self) -> int:
        n = self._mgr.fetchone("SELECT COUNT(*) AS n FROM productos")["n"]
        if n > 0:
            return 0
        ejemplos = [
            ("P001", "Laptop Dell XPS 13", "Laptop ultra portátil de 13 pulgadas", 800.0, 1200.0, 15, "Electrónica"),
            ("P002", "Monitor LG 27'", "Monitor 4K IPS", 250.0, 350.0, 30, "Monitores"),
            ("P003", "Teclado Mecánico Keychron", "Teclado mecánico Bluetooth", 60.0, 100.0, 50, "Periféricos"),
        ]
        with self._mgr.transaction() as conn:
            for codigo, nombre, desc, pc, pv, stock, cat in ejemplos:
                conn.execute(
                    """
                    INSERT INTO productos (codigo, nombre, descripcion, precio_compra,
                                           precio_venta, stock, categoria)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (codigo, nombre, desc, pc, pv, stock, cat),
                )
        return len(ejemplos)

    # ------------------------------------------------------------------
    # Lecturas
    # ------------------------------------------------------------------
    def listar(self, incluir_inactivos: bool = False) -> list[Producto]:
        q = "SELECT * FROM productos"
        if not incluir_inactivos:
            q += " WHERE activo = 1"
        q += " ORDER BY nombre"
        return [self._row_a_entidad(r) for r in self._mgr.fetchall(q)]

    def obtener(self, producto_id: int) -> Optional[Producto]:
        row = self._mgr.fetchone("SELECT * FROM productos WHERE id=?", (producto_id,))
        return self._row_a_entidad(row) if row else None

    def obtener_por_codigo(self, codigo: str) -> Optional[Producto]:
        row = self._mgr.fetchone("SELECT * FROM productos WHERE codigo=?", (codigo,))
        return self._row_a_entidad(row) if row else None

    # ------------------------------------------------------------------
    # Escrituras
    # ------------------------------------------------------------------
    def crear(
        self,
        *,
        codigo: str,
        nombre: str,
        descripcion: str,
        precio_compra: float,
        precio_venta: float,
        stock: int,
        categoria: str,
    ) -> Producto:
        with self._mgr.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO productos (codigo, nombre, descripcion,
                                       precio_compra, precio_venta, stock, categoria)
                VALUES (?,?,?,?,?,?,?)
                """,
                (codigo, nombre, descripcion, precio_compra, precio_venta, stock, categoria),
            )
            pid = cur.lastrowid
        creado = self.obtener(pid)
        assert creado is not None
        return creado

    def actualizar(
        self,
        producto_id: int,
        *,
        codigo: str,
        nombre: str,
        descripcion: str,
        precio_compra: float,
        precio_venta: float,
        stock: int,
        categoria: str,
    ) -> Optional[Producto]:
        cur = self._mgr.execute(
            """
            UPDATE productos
               SET codigo=?, nombre=?, descripcion=?,
                   precio_compra=?, precio_venta=?, stock=?, categoria=?,
                   fecha_actualizacion=datetime('now')
             WHERE id=?
            """,
            (codigo, nombre, descripcion, precio_compra, precio_venta, stock, categoria, producto_id),
        )
        if cur.rowcount == 0:
            return None
        return self.obtener(producto_id)

    def eliminar(self, producto_id: int) -> bool:
        """Baja lógica: marca activo=0 (evita huérfanos en facturas antiguas)."""
        cur = self._mgr.execute(
            "UPDATE productos SET activo=0, fecha_actualizacion=datetime('now') WHERE id=?",
            (producto_id,),
        )
        return cur.rowcount > 0

    def eliminar_duro(self, producto_id: int) -> bool:
        """Baja física. Usar solo en tests o con confirmación del usuario."""
        cur = self._mgr.execute("DELETE FROM productos WHERE id=?", (producto_id,))
        return cur.rowcount > 0

    def actualizar_stock(self, producto_id: int, delta: int) -> Optional[int]:
        """Suma `delta` al stock (puede ser negativo). Devuelve stock nuevo."""
        with self._mgr.transaction() as conn:
            row = conn.execute(
                "SELECT stock FROM productos WHERE id=?", (producto_id,)
            ).fetchone()
            if row is None:
                return None
            nuevo = row["stock"] + delta
            conn.execute(
                "UPDATE productos SET stock=?, fecha_actualizacion=datetime('now') WHERE id=?",
                (nuevo, producto_id),
            )
        return nuevo

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    @staticmethod
    def _row_a_entidad(row) -> Producto:
        return Producto(
            id=row["id"],
            codigo=row["codigo"],
            nombre=row["nombre"],
            descripcion=row["descripcion"],
            precio_compra=row["precio_compra"],
            precio_venta=row["precio_venta"],
            stock=row["stock"],
            categoria=row["categoria"],
        )
