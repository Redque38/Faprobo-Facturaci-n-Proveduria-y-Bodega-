"""
SyncService — puente SQLite local ↔ MotherDuck (DuckDB).

Dos responsabilidades:

1. **Push**: envía al servidor analítico las facturas locales cuyo flag
   `sync_duckdb = 0` (y que no hayan agotado los 3 reintentos). Para cada
   factura se replica también sus líneas, cuotas y pagos.

2. **Fetch**: baja un rango del histórico (para `FacturacionModel.cargar_historial`).

Se dispara:
- Manualmente desde la UI (botón "Sincronizar analytics").
- Automáticamente cuando llega `CierreCajaSolicitado` al bus.

La implementación es SÍNCRONA: el EventBus y los handlers del presenter
corren en el hilo UI. Si en el futuro se vuelve pesado (muchas facturas /
red lenta), se puede mover a un QThread sin cambiar la API.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from time import perf_counter
from typing import Optional

from core import config
from core.db.duckdb_client import DuckDBClient, DuckDBConfigError
from core.event_bus import EventBus
from events.facturacion_events import (
    CierreCajaSolicitado,
    SincronizacionCompletada,
    SincronizacionFallida,
    SincronizacionIniciada,
)
from features.facturacion.repository import FacturaRepository

log = logging.getLogger(__name__)


class SyncService:
    """Orquestador de la sincronización con MotherDuck."""

    def __init__(
        self,
        event_bus: EventBus,
        repository: FacturaRepository,
        duckdb_client: Optional[DuckDBClient] = None,
        sucursal_id: Optional[int] = None,
    ) -> None:
        self._bus = event_bus
        self._repo = repository
        self._client = duckdb_client  # lazy: se crea al primer uso si es None
        self._sucursal_id = sucursal_id or config.sucursal_id()
        self._suscribir_eventos()

    # ------------------------------------------------------------------
    # Inicialización del cliente (perezosa)
    # ------------------------------------------------------------------
    def _cliente(self) -> DuckDBClient:
        if self._client is None:
            self._client = DuckDBClient.from_config()
        return self._client

    def _suscribir_eventos(self) -> None:
        # Cierre de caja ⇒ push automático (política b).
        self._bus.subscribe(CierreCajaSolicitado, self._on_cierre_caja)

    def _on_cierre_caja(self, _ev: CierreCajaSolicitado) -> None:
        try:
            self.push_pendientes()
        except Exception as exc:  # noqa: BLE001
            log.exception("Falló el push automático tras cierre de caja.")
            self._bus.publish(SincronizacionFallida(error=str(exc), reintentos=0))

    # ------------------------------------------------------------------
    # PUSH local → MotherDuck
    # ------------------------------------------------------------------
    def push_pendientes(
        self,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        limite: Optional[int] = None,
    ) -> int:
        """
        Empuja todas las facturas con `sync_duckdb=0` y `sync_attempts<3`.

        - Reintenta por factura individualmente; un fallo en una no aborta
          el resto. La factura fallida suma 1 intento.
        - Publica SincronizacionIniciada / Completada / Fallida según corresponda.
        - Devuelve cantidad de facturas efectivamente sincronizadas.
        """
        hoy = datetime.now()
        d_ini = desde or datetime.combine(date.today(), datetime.min.time())
        d_fin = hasta or hoy
        self._bus.publish(SincronizacionIniciada(desde=d_ini, hasta=d_fin))
        t0 = perf_counter()

        try:
            cliente = self._cliente()
        except DuckDBConfigError as exc:
            # Sin token/config, no podemos sincronizar. Fallamos ruidoso.
            self._bus.publish(SincronizacionFallida(error=str(exc), reintentos=0))
            return 0

        pendientes = self._repo.listar_pendientes_sync(limite=limite)
        if not pendientes:
            self._bus.publish(SincronizacionCompletada(
                registros_enviados=0, duracion_segundos=perf_counter() - t0,
            ))
            return 0

        enviadas: list[int] = []
        for cabecera in pendientes:
            fid = cabecera["id"]
            try:
                completa = self._repo.obtener_factura_completa(fid)
                if not completa:
                    # Raro — se borró entre medias. Marca error y sigue.
                    self._repo.registrar_fallo_sync(fid, "Factura no encontrada al sincronizar.")
                    continue
                self._upsert_factura(cliente, completa)
                enviadas.append(fid)
            except Exception as exc:  # noqa: BLE001
                log.exception("Fallo sincronizando factura #%s", fid)
                self._repo.registrar_fallo_sync(fid, f"{type(exc).__name__}: {exc}")

        if enviadas:
            self._repo.marcar_sincronizadas(enviadas)

        dur = perf_counter() - t0
        fallidas = len(pendientes) - len(enviadas)
        if fallidas == 0:
            self._bus.publish(SincronizacionCompletada(
                registros_enviados=len(enviadas), duracion_segundos=dur,
            ))
        else:
            self._bus.publish(SincronizacionFallida(
                error=f"{fallidas} de {len(pendientes)} facturas fallaron.",
                reintentos=fallidas,
            ))
        return len(enviadas)

    # ------------------------------------------------------------------
    # UPSERT de una factura completa (cabecera + líneas + cuotas + pagos)
    # ------------------------------------------------------------------
    def _upsert_factura(self, cliente: DuckDBClient, f: dict) -> None:
        """
        Transacción remota: borra líneas/cuotas/pagos existentes de esta
        factura-sucursal y re-inserta el estado local autoritativo.
        La cabecera usa `INSERT OR REPLACE`.
        """
        s_id = self._sucursal_id
        fid = f["id"]
        with cliente.transaction():
            # Cabecera
            cliente.execute(
                """
                INSERT OR REPLACE INTO facturas
                    (id, sucursal_id, tipo, entidad_id, subtotal, descuento,
                     impuesto, total, estado, es_electronica,
                     fecha_creacion, fecha_actualizacion)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    fid, s_id, f["tipo"], f["entidad_id"],
                    f["subtotal"], f["descuento"], f["impuesto"], f["total"],
                    f["estado"], bool(f.get("es_electronica", 0)),
                    f["fecha_creacion"], f.get("fecha_actualizacion"),
                ),
            )
            # Hijos: borramos y re-insertamos para quedar idénticos al local.
            cliente.execute(
                "DELETE FROM factura_lineas WHERE factura_id=? AND sucursal_id=?",
                (fid, s_id),
            )
            lineas = f.get("lineas") or []
            if lineas:
                cliente.executemany(
                    """
                    INSERT INTO factura_lineas
                        (id, sucursal_id, factura_id, producto_id, descripcion,
                         cantidad, precio_unitario, descuento_linea, total_linea)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    [
                        (
                            l["id"], s_id, fid, l["producto_id"], l["descripcion"],
                            l["cantidad"], l["precio_unitario"],
                            l.get("descuento_linea", 0), l["total_linea"],
                        )
                        for l in lineas
                    ],
                )

            cliente.execute(
                "DELETE FROM factura_cuotas WHERE factura_id=? AND sucursal_id=?",
                (fid, s_id),
            )
            cuotas = f.get("cuotas") or []
            if cuotas:
                cliente.executemany(
                    """
                    INSERT INTO factura_cuotas
                        (id, sucursal_id, factura_id, numero_cuota, monto,
                         fecha_vencimiento, pagada, fecha_pago)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    [
                        (
                            c["id"], s_id, fid, c["numero_cuota"], c["monto"],
                            c["fecha_vencimiento"], bool(c.get("pagada", 0)),
                            c.get("fecha_pago"),
                        )
                        for c in cuotas
                    ],
                )

            cliente.execute(
                "DELETE FROM factura_pagos WHERE factura_id=? AND sucursal_id=?",
                (fid, s_id),
            )
            pagos = f.get("pagos") or []
            if pagos:
                cliente.executemany(
                    """
                    INSERT INTO factura_pagos
                        (id, sucursal_id, factura_id, monto, fecha_pago, metodo)
                    VALUES (?,?,?,?,?,?)
                    """,
                    [
                        (
                            p["id"], s_id, fid, p["monto"],
                            p["fecha_pago"], p.get("metodo", "efectivo"),
                        )
                        for p in pagos
                    ],
                )

    # ------------------------------------------------------------------
    # FETCH MotherDuck → caché local (downloader para cargar_historial)
    # ------------------------------------------------------------------
    def fetch_historial(self, desde: datetime, hasta: datetime) -> list[dict]:
        """
        Baja facturas (cabeceras) de MotherDuck en el rango [desde, hasta].
        El formato es compatible con `FacturaRepository.volcar_historia_temp`.
        Filtra por `sucursal_id` local.
        """
        cliente = self._cliente()
        d_ini = desde.isoformat() if hasattr(desde, "isoformat") else str(desde)
        d_fin = hasta.isoformat() if hasattr(hasta, "isoformat") else str(hasta)

        rows = cliente.fetchall(
            """
            SELECT id, tipo, entidad_id, subtotal, descuento, impuesto,
                   total, estado, es_electronica, fecha_creacion
            FROM facturas
            WHERE sucursal_id = ?
              AND fecha_creacion BETWEEN CAST(? AS TIMESTAMP)
                                     AND CAST(? AS TIMESTAMP)
            ORDER BY fecha_creacion DESC
            """,
            (self._sucursal_id, d_ini, d_fin),
        )

        # Normaliza tipos que DuckDB devuelve nativos a algo que SQLite
        # acepta (bool → int, datetime → iso string).
        out: list[dict] = []
        for r in rows:
            fc = r["fecha_creacion"]
            if isinstance(fc, datetime):
                fc = fc.isoformat(sep=" ")
            out.append({
                "id": r["id"],
                "tipo": r["tipo"],
                "entidad_id": r["entidad_id"],
                "subtotal": float(r["subtotal"] or 0),
                "descuento": float(r["descuento"] or 0),
                "impuesto": float(r["impuesto"] or 0),
                "total": float(r["total"] or 0),
                "estado": r["estado"],
                "es_electronica": int(bool(r["es_electronica"])),
                "fecha_creacion": fc,
            })
        return out

    # ------------------------------------------------------------------
    # Helpers públicos
    # ------------------------------------------------------------------
    def como_downloader(self):
        """
        Devuelve una función compatible con
        `FacturacionModel.set_historial_downloader` (firma: desde, hasta -> list).
        """
        return self.fetch_historial
