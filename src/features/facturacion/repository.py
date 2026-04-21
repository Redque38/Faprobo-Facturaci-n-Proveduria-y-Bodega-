"""
FacturaRepository: aísla el acceso a SQLite del módulo de Facturación.

El model.py solo llama a métodos de este repositorio. Si mañana cambia
el backend (p.ej. a duckdb directo, o a Supabase), se reimplementa acá
sin tocar la lógica de negocio ni los presenters.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from core.db.sqlite_manager import SqliteManager


class FacturaRepository:
    def __init__(self, manager: SqliteManager):
        self._mgr = manager

    # ------------------------------------------------------------------
    # Creación
    # ------------------------------------------------------------------
    def crear_factura(
        self,
        *,
        tipo: str,
        entidad_id: int,
        subtotal: float,
        descuento_global: float,
        impuesto: float,
        total: float,
        lineas: list[dict],
        cuotas: Optional[list[dict]] = None,
        es_electronica: bool = False,
    ) -> int:
        """Inserta cabecera + líneas + cuotas en una sola transacción."""
        with self._mgr.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO facturas
                    (tipo, entidad_id, subtotal, descuento, impuesto, total, es_electronica)
                VALUES (?,?,?,?,?,?,?)
                """,
                (tipo, entidad_id, subtotal, descuento_global, impuesto, total, int(es_electronica)),
            )
            factura_id = cur.lastrowid

            for linea in lineas:
                total_linea = (
                    linea["cantidad"] * linea["precio_unitario"]
                    - linea.get("descuento_linea", 0)
                )
                conn.execute(
                    """
                    INSERT INTO factura_lineas
                        (factura_id, producto_id, descripcion, cantidad,
                         precio_unitario, descuento_linea, total_linea)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        factura_id,
                        linea["producto_id"],
                        linea["descripcion"],
                        linea["cantidad"],
                        linea["precio_unitario"],
                        linea.get("descuento_linea", 0),
                        total_linea,
                    ),
                )

            if cuotas:
                for i, cuota in enumerate(cuotas, start=1):
                    conn.execute(
                        """
                        INSERT INTO factura_cuotas
                            (factura_id, numero_cuota, monto, fecha_vencimiento)
                        VALUES (?,?,?,?)
                        """,
                        (factura_id, i, cuota["monto"], cuota["fecha_vencimiento"]),
                    )
        return factura_id

    def agregar_linea(self, factura_id: int, linea: dict) -> None:
        total_linea = (
            linea["cantidad"] * linea["precio_unitario"]
            - linea.get("descuento_linea", 0)
        )
        with self._mgr.transaction() as conn:
            conn.execute(
                """
                INSERT INTO factura_lineas
                    (factura_id, producto_id, descripcion, cantidad,
                     precio_unitario, descuento_linea, total_linea)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    factura_id,
                    linea["producto_id"],
                    linea["descripcion"],
                    linea["cantidad"],
                    linea["precio_unitario"],
                    linea.get("descuento_linea", 0),
                    total_linea,
                ),
            )
            self._recalcular_total(conn, factura_id)

    # ------------------------------------------------------------------
    # Modificaciones
    # ------------------------------------------------------------------
    def anular_factura(self, factura_id: int) -> None:
        # Resetea sync_duckdb para que el cambio de estado viaje al analytics.
        self._mgr.execute(
            "UPDATE facturas "
            "SET estado='anulada', "
            "    fecha_actualizacion=datetime('now'), "
            "    sync_duckdb=0, sync_attempts=0, sync_last_error=NULL "
            "WHERE id=?",
            (factura_id,),
        )

    def registrar_pago(
        self, factura_id: int, monto: float, metodo: str = "efectivo"
    ) -> bool:
        """
        Inserta el pago y marca la factura como 'pagada' si se alcanzó el total.
        Devuelve True si la factura quedó pagada completa.
        """
        with self._mgr.transaction() as conn:
            conn.execute(
                "INSERT INTO factura_pagos (factura_id, monto, metodo) VALUES (?,?,?)",
                (factura_id, monto, metodo),
            )
            row = conn.execute(
                "SELECT total FROM facturas WHERE id=?", (factura_id,)
            ).fetchone()
            if row is None:
                return False
            total_pagado = conn.execute(
                "SELECT COALESCE(SUM(monto),0) FROM factura_pagos WHERE factura_id=?",
                (factura_id,),
            ).fetchone()[0]
            if total_pagado >= row["total"]:
                conn.execute(
                    "UPDATE facturas "
                    "SET estado='pagada', "
                    "    fecha_actualizacion=datetime('now'), "
                    "    sync_duckdb=0, sync_attempts=0, sync_last_error=NULL "
                    "WHERE id=?",
                    (factura_id,),
                )
                return True
            # Pago parcial: también invalidamos sync para reflejar el nuevo pago.
            conn.execute(
                "UPDATE facturas "
                "SET sync_duckdb=0, sync_attempts=0, sync_last_error=NULL "
                "WHERE id=?",
                (factura_id,),
            )
            return False

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def obtener_factura(self, factura_id: int) -> Optional[dict]:
        row = self._mgr.fetchone("SELECT * FROM facturas WHERE id=?", (factura_id,))
        if not row:
            return None
        lineas = self._mgr.fetchall(
            "SELECT * FROM factura_lineas WHERE factura_id=?", (factura_id,)
        )
        cuotas = self._mgr.fetchall(
            "SELECT * FROM factura_cuotas WHERE factura_id=? ORDER BY numero_cuota",
            (factura_id,),
        )
        pagos = self._mgr.fetchall(
            "SELECT * FROM factura_pagos WHERE factura_id=? ORDER BY fecha_pago",
            (factura_id,),
        )
        return {
            **dict(row),
            "lineas": [dict(r) for r in lineas],
            "cuotas": [dict(r) for r in cuotas],
            "pagos": [dict(r) for r in pagos],
        }

    def listar_facturas(
        self, tipo: Optional[str] = None, estado: Optional[str] = None
    ) -> list[dict]:
        query = "SELECT * FROM facturas WHERE 1=1"
        params: list = []
        if tipo:
            query += " AND tipo=?"
            params.append(tipo)
        if estado:
            query += " AND estado=?"
            params.append(estado)
        query += " ORDER BY fecha_creacion DESC"
        return [dict(r) for r in self._mgr.fetchall(query, tuple(params))]

    def listar_hoy(
        self, tipo: Optional[str] = None, estado: Optional[str] = None
    ) -> list[dict]:
        """Facturas creadas hoy (zona local del equipo)."""
        # `fecha_creacion` se guarda en UTC (DEFAULT datetime('now'));
        # convertimos ambos lados a localtime para evitar desfases cerca de medianoche.
        query = (
            "SELECT * FROM facturas "
            "WHERE date(fecha_creacion,'localtime') = date('now','localtime')"
        )
        params: list = []
        if tipo:
            query += " AND tipo=?"
            params.append(tipo)
        if estado:
            query += " AND estado=?"
            params.append(estado)
        query += " ORDER BY fecha_creacion DESC"
        return [dict(r) for r in self._mgr.fetchall(query, tuple(params))]

    def listar_por_rango(
        self, desde: date | datetime, hasta: date | datetime
    ) -> list[dict]:
        d_ini = desde.isoformat() if hasattr(desde, "isoformat") else str(desde)
        d_fin = hasta.isoformat() if hasattr(hasta, "isoformat") else str(hasta)
        # Usamos datetime() para que el rango se compare como fecha real y
        # no como texto (evita mismatch entre formatos "T" y " ").
        rows = self._mgr.fetchall(
            "SELECT * FROM facturas "
            "WHERE datetime(fecha_creacion) BETWEEN datetime(?) AND datetime(?) "
            "ORDER BY datetime(fecha_creacion) DESC",
            (d_ini, d_fin),
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Sincronización con DuckDB (solo el estado local; la red vive en otra capa)
    # ------------------------------------------------------------------
    # Política: después de 3 intentos fallidos la factura deja de pujarse.
    # Requiere intervención (ej. botón "reintentar sync") que limpie
    # sync_attempts a 0.
    MAX_SYNC_ATTEMPTS = 3

    def listar_pendientes_sync(self, limite: Optional[int] = None) -> list[dict]:
        q = (
            "SELECT * FROM facturas "
            "WHERE sync_duckdb = 0 AND sync_attempts < ? "
            "ORDER BY id ASC"
        )
        params: tuple = (self.MAX_SYNC_ATTEMPTS,)
        if limite is not None:
            q += " LIMIT ?"
            params = (self.MAX_SYNC_ATTEMPTS, int(limite))
        return [dict(r) for r in self._mgr.fetchall(q, params)]

    def reintentar_sync(self, factura_id: int) -> None:
        """Resetea el contador de reintentos para una factura bloqueada."""
        self._mgr.execute(
            "UPDATE facturas "
            "SET sync_attempts=0, sync_last_error=NULL "
            "WHERE id=?",
            (factura_id,),
        )

    def obtener_factura_completa(self, factura_id: int) -> Optional[dict]:
        """
        Variante de `obtener_factura` orientada al push a DuckDB.
        Incluye cabecera + líneas + cuotas + pagos.
        """
        return self.obtener_factura(factura_id)

    def marcar_sincronizadas(self, ids: list[int]) -> None:
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        with self._mgr.transaction() as conn:
            conn.execute(
                f"UPDATE facturas SET sync_duckdb = 1, sync_last_error = NULL "
                f"WHERE id IN ({placeholders})",
                tuple(ids),
            )

    def registrar_fallo_sync(self, factura_id: int, error: str) -> None:
        self._mgr.execute(
            "UPDATE facturas "
            "SET sync_attempts = sync_attempts + 1, sync_last_error = ? "
            "WHERE id = ?",
            (error, factura_id),
        )

    # ------------------------------------------------------------------
    # Caché histórica local (se llena al consultar DuckDB)
    # ------------------------------------------------------------------
    def volcar_historia_temp(self, registros: list[dict], periodo_key: str) -> int:
        """
        Vuelca resultados del servidor DuckDB en la caché local.
        Usa INSERT OR REPLACE sobre (id, periodo_key) para permitir refrescar.
        """
        if not registros:
            return 0
        with self._mgr.transaction() as conn:
            for r in registros:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO facturas_historia_temp
                        (id, tipo, entidad_id, subtotal, descuento, impuesto,
                         total, estado, es_electronica, fecha_creacion, periodo_key)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        r["id"], r["tipo"], r["entidad_id"],
                        r["subtotal"], r["descuento"], r["impuesto"],
                        r["total"], r["estado"], int(r.get("es_electronica", 0)),
                        r["fecha_creacion"], periodo_key,
                    ),
                )
        return len(registros)

    def leer_historia_temp(self, periodo_key: str) -> list[dict]:
        rows = self._mgr.fetchall(
            "SELECT * FROM facturas_historia_temp "
            "WHERE periodo_key = ? ORDER BY fecha_creacion DESC",
            (periodo_key,),
        )
        return [dict(r) for r in rows]

    def leer_historia_temp_por_rango(
        self, desde: date | datetime, hasta: date | datetime
    ) -> list[dict]:
        """Devuelve todas las facturas cacheadas que caigan en [desde, hasta]."""
        d_ini = desde.isoformat() if hasattr(desde, "isoformat") else str(desde)
        d_fin = hasta.isoformat() if hasattr(hasta, "isoformat") else str(hasta)
        # Usamos datetime() para que el BETWEEN compare fechas reales y
        # no strings (evita mismatch entre formatos "T" y " ").
        rows = self._mgr.fetchall(
            "SELECT * FROM facturas_historia_temp "
            "WHERE datetime(fecha_creacion) BETWEEN datetime(?) AND datetime(?) "
            "ORDER BY datetime(fecha_creacion) DESC",
            (d_ini, d_fin),
        )
        return [dict(r) for r in rows]

    def limpiar_historia_temp(self, periodo_key: Optional[str] = None) -> int:
        if periodo_key is None:
            cur = self._mgr.execute("DELETE FROM facturas_historia_temp")
        else:
            cur = self._mgr.execute(
                "DELETE FROM facturas_historia_temp WHERE periodo_key = ?",
                (periodo_key,),
            )
        return cur.rowcount or 0

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    @staticmethod
    def _recalcular_total(conn, factura_id: int) -> None:
        row = conn.execute(
            "SELECT descuento, impuesto FROM facturas WHERE id=?", (factura_id,)
        ).fetchone()
        if not row:
            return
        subtotal = conn.execute(
            "SELECT COALESCE(SUM(total_linea),0) FROM factura_lineas WHERE factura_id=?",
            (factura_id,),
        ).fetchone()[0]
        base = subtotal - row["descuento"]
        total = round(base + row["impuesto"], 2)
        # Reset de sync: la cabecera cambió → hay que re-empujarla.
        conn.execute(
            "UPDATE facturas "
            "SET subtotal=?, total=?, fecha_actualizacion=datetime('now'), "
            "    sync_duckdb=0, sync_attempts=0, sync_last_error=NULL "
            "WHERE id=?",
            (subtotal, total, factura_id),
        )
