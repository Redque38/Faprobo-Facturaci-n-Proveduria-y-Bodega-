"""
PosRepository — acceso a datos del módulo Punto de Venta.

Consulta la base catalogo.db para búsqueda de productos.
No duplica lógica de facturación: delega a FacturacionModel.
"""
from __future__ import annotations

from typing import Optional

from core.db.sqlite_manager import SqliteManager


class PosRepository:
    """Consultas de productos para el punto de venta."""

    def __init__(self, mgr: SqliteManager) -> None:
        self._mgr = mgr

    # ------------------------------------------------------------------
    # Búsqueda de productos
    # ------------------------------------------------------------------

    def buscar_productos(self, texto: str) -> list[dict]:
        """
        Retorna hasta 30 productos activos que coincidan con `texto`
        en nombre o código. Solo incluye productos con stock > 0.
        """
        q = f"%{texto}%"
        sql = """
            SELECT  id, codigo, nombre, descripcion,
                    precio_venta, stock, categoria
            FROM    productos
            WHERE   activo = 1
              AND   stock  > 0
              AND   (LOWER(nombre) LIKE LOWER(?) OR LOWER(codigo) LIKE LOWER(?))
            ORDER   BY nombre
            LIMIT   30
        """
        rows = self._mgr.fetchall(sql, (q, q))
        return [dict(r) for r in rows]

    def obtener_producto(self, producto_id: int) -> Optional[dict]:
        """Obtiene un producto por ID (incluye inactivos y sin stock para validación)."""
        row = self._mgr.fetchone(
            "SELECT id, codigo, nombre, precio_venta, stock, activo "
            "FROM productos WHERE id = ?",
            (producto_id,),
        )
        return dict(row) if row else None
