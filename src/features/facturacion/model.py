import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.event_bus import EventBus
from events.facturacion_events import (
    FacturaCreada, FacturaAnulada, FacturaPagada,
    CuotaRegistrada, StockSolicitado, StockDescontado,
    StockInsuficiente, SincronizacionIniciada,
    SincronizacionCompletada, SincronizacionFallida,
)


DB_PATH = Path("data/faprobo.db")


class FacturacionModel:
    """
    Modelo del módulo de facturación.
    - Transacciones diarias → SQLite local (sin internet).
    - Reportes analíticos   → DuckDB remoto (bajo demanda).
    """

    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        self._suscribir_eventos()

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._crear_tablas()

    def _crear_tablas(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS facturas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo            TEXT    NOT NULL CHECK(tipo IN ('venta','compra')),
            entidad_id      INTEGER NOT NULL,
            subtotal        REAL    NOT NULL DEFAULT 0,
            descuento       REAL    NOT NULL DEFAULT 0,
            impuesto        REAL    NOT NULL DEFAULT 0,
            total           REAL    NOT NULL DEFAULT 0,
            estado          TEXT    NOT NULL DEFAULT 'pendiente'
                                    CHECK(estado IN ('pendiente','pagada','anulada')),
            es_electronica  INTEGER NOT NULL DEFAULT 0,
            fecha_creacion  TEXT    NOT NULL DEFAULT (datetime('now')),
            fecha_actualizacion TEXT
        );

        CREATE TABLE IF NOT EXISTS factura_lineas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id      INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
            producto_id     INTEGER NOT NULL,
            descripcion     TEXT    NOT NULL,
            cantidad        REAL    NOT NULL,
            precio_unitario REAL    NOT NULL,
            descuento_linea REAL    NOT NULL DEFAULT 0,
            total_linea     REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS factura_cuotas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id      INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
            numero_cuota    INTEGER NOT NULL,
            monto           REAL    NOT NULL,
            fecha_vencimiento TEXT  NOT NULL,
            pagada          INTEGER NOT NULL DEFAULT 0,
            fecha_pago      TEXT
        );

        CREATE TABLE IF NOT EXISTS factura_pagos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id      INTEGER NOT NULL REFERENCES facturas(id),
            monto           REAL    NOT NULL,
            fecha_pago      TEXT    NOT NULL DEFAULT (datetime('now')),
            metodo          TEXT    NOT NULL DEFAULT 'efectivo'
        );
        """
        with self._lock:
            self._conn.executescript(sql)
            self._conn.commit()

    def _suscribir_eventos(self) -> None:
        self._bus.subscribe(StockDescontado, self._on_stock_descontado)
        self._bus.subscribe(StockInsuficiente, self._on_stock_insuficiente)

    # ------------------------------------------------------------------
    # Operaciones CRUD — facturas
    # ------------------------------------------------------------------

    def crear_factura(
        self,
        tipo: str,
        entidad_id: int,
        lineas: list[dict],
        descuento_global: float = 0.0,
        impuesto_pct: float = 0.13,       # IVA Costa Rica 13%
        cuotas: Optional[list[dict]] = None,
        es_electronica: bool = False,
    ) -> int:
        """
        Crea una factura, solicita descuento de stock y dispara eventos.
        Retorna el ID de la factura creada.
        """
        subtotal = sum(
            l["cantidad"] * l["precio_unitario"] - l.get("descuento_linea", 0)
            for l in lineas
        )
        base_gravable = subtotal - descuento_global
        impuesto = round(base_gravable * impuesto_pct, 2)
        total = round(base_gravable + impuesto, 2)

        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO facturas
                   (tipo, entidad_id, subtotal, descuento, impuesto, total, es_electronica)
                   VALUES (?,?,?,?,?,?,?)""",
                (tipo, entidad_id, subtotal, descuento_global, impuesto, total, int(es_electronica)),
            )
            factura_id = cur.lastrowid

            for linea in lineas:
                total_linea = (
                    linea["cantidad"] * linea["precio_unitario"]
                    - linea.get("descuento_linea", 0)
                )
                self._conn.execute(
                    """INSERT INTO factura_lineas
                       (factura_id, producto_id, descripcion, cantidad,
                        precio_unitario, descuento_linea, total_linea)
                       VALUES (?,?,?,?,?,?,?)""",
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
                    self._conn.execute(
                        """INSERT INTO factura_cuotas
                           (factura_id, numero_cuota, monto, fecha_vencimiento)
                           VALUES (?,?,?,?)""",
                        (factura_id, i, cuota["monto"], cuota["fecha_vencimiento"]),
                    )

            self._conn.commit()

        # Solicitar descuento de stock para facturas de venta
        if tipo == "venta":
            for linea in lineas:
                self._bus.publish(StockSolicitado(
                    producto_id=linea["producto_id"],
                    cantidad=int(linea["cantidad"]),
                    factura_id=factura_id,
                ))

        self._bus.publish(FacturaCreada(
            factura_id=factura_id,
            tipo=tipo,
            cliente_proveedor_id=entidad_id,
            total=total,
        ))

        # TODO ChepelCR — enviar a Hacienda si es_electronica=True

        return factura_id

    def anular_factura(self, factura_id: int, motivo: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE facturas SET estado='anulada', fecha_actualizacion=datetime('now') WHERE id=?",
                (factura_id,),
            )
            self._conn.commit()
        self._bus.publish(FacturaAnulada(factura_id=factura_id, motivo=motivo))

    def registrar_pago(self, factura_id: int, monto: float, metodo: str = "efectivo") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO factura_pagos (factura_id, monto, metodo) VALUES (?,?,?)",
                (factura_id, monto, metodo),
            )
            # Marcar factura como pagada si el total está cubierto
            row = self._conn.execute(
                "SELECT total FROM facturas WHERE id=?", (factura_id,)
            ).fetchone()
            total_pagado = self._conn.execute(
                "SELECT COALESCE(SUM(monto),0) FROM factura_pagos WHERE factura_id=?",
                (factura_id,),
            ).fetchone()[0]
            if row and total_pagado >= row["total"]:
                self._conn.execute(
                    "UPDATE facturas SET estado='pagada', fecha_actualizacion=datetime('now') WHERE id=?",
                    (factura_id,),
                )
            self._conn.commit()
        self._bus.publish(FacturaPagada(factura_id=factura_id, monto_pagado=monto))

    def agregar_linea(self, factura_id: int, linea: dict) -> None:
        """Permite añadir ítems a una factura existente (estado pendiente)."""
        total_linea = (
            linea["cantidad"] * linea["precio_unitario"]
            - linea.get("descuento_linea", 0)
        )
        with self._lock:
            self._conn.execute(
                """INSERT INTO factura_lineas
                   (factura_id, producto_id, descripcion, cantidad,
                    precio_unitario, descuento_linea, total_linea)
                   VALUES (?,?,?,?,?,?,?)""",
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
            self._recalcular_total(factura_id)
            self._conn.commit()

    def obtener_factura(self, factura_id: int) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM facturas WHERE id=?", (factura_id,)
        ).fetchone()
        if not row:
            return None
        lineas = self._conn.execute(
            "SELECT * FROM factura_lineas WHERE factura_id=?", (factura_id,)
        ).fetchall()
        cuotas = self._conn.execute(
            "SELECT * FROM factura_cuotas WHERE factura_id=? ORDER BY numero_cuota",
            (factura_id,),
        ).fetchall()
        return {
            **dict(row),
            "lineas": [dict(l) for l in lineas],
            "cuotas": [dict(c) for c in cuotas],
        }

    def listar_facturas(self, tipo: Optional[str] = None, estado: Optional[str] = None) -> list[dict]:
        query = "SELECT * FROM facturas WHERE 1=1"
        params: list = []
        if tipo:
            query += " AND tipo=?"; params.append(tipo)
        if estado:
            query += " AND estado=?"; params.append(estado)
        query += " ORDER BY fecha_creacion DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Respuestas a eventos de bodega
    # ------------------------------------------------------------------

    def _on_stock_descontado(self, evento: StockDescontado) -> None:
        # Stock confirmado — no se requiere acción adicional en el modelo
        pass

    def _on_stock_insuficiente(self, evento: StockInsuficiente) -> None:
        # Anular automáticamente si bodega reporta stock insuficiente
        self.anular_factura(
            evento.factura_id,
            motivo=f"Stock insuficiente: producto {evento.producto_id} "
                   f"(disponible: {evento.cantidad_disponible}, solicitado: {evento.cantidad_solicitada})",
        )

    # ------------------------------------------------------------------
    # Reportes analíticos — DuckDB remoto
    # ------------------------------------------------------------------

    def sincronizar_con_duckdb(self, desde: datetime, hasta: datetime) -> None:
        """
        Exporta las facturas del período a DuckDB remoto para análisis.
        Solo se llama quincenalmente/mensualmente.
        """
        import threading
        threading.Thread(
            target=self._sincronizar_background,
            args=(desde, hasta),
            daemon=True,
        ).start()

    def _sincronizar_background(self, desde: datetime, hasta: datetime) -> None:
        self._bus.publish(SincronizacionIniciada(desde=desde, hasta=hasta))
        inicio = datetime.now()
        try:
            import os
            import requests  # pip: requests

            token = os.environ.get("DUCKDB_TOKEN")
            endpoint = os.environ.get("DUCKDB_ENDPOINT")

            if not token or not endpoint:
                raise EnvironmentError("DUCKDB_TOKEN o DUCKDB_ENDPOINT no configurados")

            facturas = self._conn.execute(
                "SELECT * FROM facturas WHERE fecha_creacion BETWEEN ? AND ?",
                (desde.isoformat(), hasta.isoformat()),
            ).fetchall()
            payload = [dict(f) for f in facturas]

            resp = requests.post(
                endpoint,
                json={"registros": payload},
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            resp.raise_for_status()

            duracion = (datetime.now() - inicio).total_seconds()
            self._bus.publish(SincronizacionCompletada(
                registros_enviados=len(payload),
                duracion_segundos=duracion,
            ))
        except Exception as exc:
            self._bus.publish(SincronizacionFallida(error=str(exc), reintentos=0))

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _recalcular_total(self, factura_id: int) -> None:
        """Recalcula el total de una factura sumando sus líneas."""
        row = self._conn.execute(
            "SELECT descuento, impuesto FROM facturas WHERE id=?", (factura_id,)
        ).fetchone()
        if not row:
            return
        subtotal = self._conn.execute(
            "SELECT COALESCE(SUM(total_linea),0) FROM factura_lineas WHERE factura_id=?",
            (factura_id,),
        ).fetchone()[0]
        base = subtotal - row["descuento"]
        total = round(base + row["impuesto"], 2)
        self._conn.execute(
            "UPDATE facturas SET subtotal=?, total=?, fecha_actualizacion=datetime('now') WHERE id=?",
            (subtotal, total, factura_id),
        )
