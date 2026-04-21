"""
BitacoraService — escritura asíncrona de auditoría.

Diseño:
  ┌─────────────────────────────────────────────────────────────┐
  │  Hilo principal (Qt)                                        │
  │   EventBus.publish(FacturaCreada) ──► handler               │
  │                                         └─► queue.put()     │  ← O(1), no bloquea
  └─────────────────────────────────────────────────────────────┘
                                               │
  ┌─────────────────────────────────────────────────────────────┐
  │  Hilo worker (daemon)                     │                 │
  │   queue.get() ◄──────────────────────────┘                 │
  │       └─► INSERT INTO bitacora …                            │
  └─────────────────────────────────────────────────────────────┘

Garantías:
  - Nunca bloquea la UI.
  - Si el INSERT falla, se descarta silenciosamente (el log NUNCA rompe la app).
  - Al cerrar la app el hilo daemon muere solo (sin joins explícitos).
  - La conexión SQLite se crea dentro del worker thread (thread-safe).
"""
from __future__ import annotations

import logging
import queue
import sqlite3
import threading
from typing import Optional

from core.event_bus import EventBus
from events.facturacion_events import (
    FacturaCreada, FacturaAnulada, FacturaPagada,
    StockDescontado, StockInsuficiente,
    PDFGenerado, ImpresionSolicitada,
    SincronizacionCompletada, SincronizacionFallida,
)
from events.pos_events import VentaCompletadaEvent
# Nota: producto_events, proveedor_events y usuario_events no se importan como
# topics porque sus modelos usan emit(string, ...) — las suscripciones son por str.

_log = logging.getLogger(__name__)

# ─── Modelo de entrada ────────────────────────────────────────────────────────

class _Entrada:
    __slots__ = ("usuario_nom", "modulo", "accion", "descripcion")

    def __init__(
        self,
        usuario_nom: str,
        modulo: str,
        accion: str,
        descripcion: str = "",
    ) -> None:
        self.usuario_nom = usuario_nom
        self.modulo      = modulo
        self.accion      = accion
        self.descripcion = descripcion


# ─── Worker asíncrono ─────────────────────────────────────────────────────────

class _BitacoraWriter:
    """
    Worker thread que consume una cola de entradas y las escribe en SQLite.
    Crea su propia conexión para evitar conflictos de threading con SqliteManager.
    """

    _INSERT = (
        "INSERT INTO bitacora (usuario_nom, modulo, accion, descripcion) "
        "VALUES (?, ?, ?, ?)"
    )

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._queue: queue.Queue[Optional[_Entrada]] = queue.Queue()
        self._thread = threading.Thread(
            target=self._run, name="BitacoraWorker", daemon=True
        )
        self._thread.start()

    def put(self, entry: _Entrada) -> None:
        """Encola una entrada — nunca bloquea el hilo llamador."""
        try:
            self._queue.put_nowait(entry)
        except Exception:
            pass   # descarte silencioso si la cola estuviera llena

    def _run(self) -> None:
        """Loop del worker: espera entradas y las persiste."""
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._ensure_schema(conn)

            while True:
                try:
                    entry = self._queue.get(timeout=1.0)
                    if entry is None:          # señal de parada (no se usa actualmente)
                        break
                    try:
                        conn.execute(
                            self._INSERT,
                            (entry.usuario_nom, entry.modulo,
                             entry.accion, entry.descripcion),
                        )
                        conn.commit()
                    except Exception as exc:
                        _log.debug("BitacoraWriter: INSERT falló — %s", exc)
                    finally:
                        self._queue.task_done()
                except queue.Empty:
                    continue
        except Exception as exc:
            _log.warning("BitacoraWorker: hilo terminó con error — %s", exc)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bitacora (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                usuario_nom TEXT NOT NULL DEFAULT 'sistema',
                modulo      TEXT NOT NULL,
                accion      TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_bitacora_ts "
            "ON bitacora(timestamp DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_bitacora_modulo "
            "ON bitacora(modulo)"
        )
        conn.commit()


# ─── Servicio principal ───────────────────────────────────────────────────────

class BitacoraService:
    """
    Se suscribe pasivamente al EventBus y registra cada acción relevante.
    No modifica ningún módulo existente — solo escucha.

    Uso:
        service = BitacoraService(event_bus, "data/bitacora.db", "admin")
        # Eso es todo — se auto-suscribe a todos los eventos necesarios.
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_path: str,
        usuario_nom: str = "sistema",
    ) -> None:
        self._bus     = event_bus
        self._usuario = usuario_nom
        self._writer  = _BitacoraWriter(db_path)
        self._suscribir()
        # Registrar el propio inicio de sesión
        self._log("sistema", "login", f"Sesión iniciada — usuario: {usuario_nom}")

    # ------------------------------------------------------------------
    # API interna
    # ------------------------------------------------------------------

    def _log(self, modulo: str, accion: str, descripcion: str = "") -> None:
        """Encola la entrada — O(1), nunca bloquea."""
        self._writer.put(_Entrada(self._usuario, modulo, accion, descripcion))

    def _safe(self, modulo: str, accion: str, desc_fn) -> None:
        """Wrapper que silencia errores al construir la descripción."""
        try:
            self._log(modulo, accion, desc_fn())
        except Exception:
            self._log(modulo, accion, "")

    # ------------------------------------------------------------------
    # Suscripciones al EventBus
    # ------------------------------------------------------------------

    def _suscribir(self) -> None:
        bus = self._bus

        # ── Facturación ──────────────────────────────────────────────
        bus.subscribe(FacturaCreada, lambda e: self._safe(
            "facturacion", "factura_creada",
            lambda: f"Factura #{e.factura_id} ({e.tipo}) — Total ₡{e.total:,.2f}",
        ))
        bus.subscribe(FacturaAnulada, lambda e: self._safe(
            "facturacion", "factura_anulada",
            lambda: f"Factura #{e.factura_id} — Motivo: {e.motivo}",
        ))
        bus.subscribe(FacturaPagada, lambda e: self._safe(
            "facturacion", "factura_pagada",
            lambda: f"Factura #{e.factura_id} — Monto ₡{e.monto_pagado:,.2f}",
        ))

        # ── Punto de Venta ───────────────────────────────────────────
        bus.subscribe(VentaCompletadaEvent, lambda e: self._safe(
            "pos", "venta_completada",
            lambda: (
                f"Factura #{e.factura_id} — "
                f"Total ₡{e.total:,.2f} — Método: {e.metodo_pago}"
            ),
        ))

        # ── Stock ────────────────────────────────────────────────────
        bus.subscribe(StockDescontado, lambda e: self._safe(
            "productos", "stock_descontado",
            lambda: (
                f"Producto #{e.producto_id} — "
                f"-{e.cantidad} unidades (stock restante: {e.stock_restante})"
            ),
        ))
        bus.subscribe(StockInsuficiente, lambda e: self._safe(
            "productos", "stock_insuficiente",
            lambda: (
                f"Producto #{e.producto_id} — "
                f"Solicitado: {e.cantidad_solicitada}, "
                f"Disponible: {e.cantidad_disponible}"
            ),
        ))

        # ── Productos ────────────────────────────────────────────────
        # ProductoModel usa emit(string, ...) → suscribir por string, no por clase
        bus.subscribe("producto_guardado", lambda e: self._safe(
            "productos",
            "producto_creado" if e.es_nuevo else "producto_actualizado",
            lambda: f"[{e.producto.codigo}] {e.producto.nombre}",
        ))
        bus.subscribe("producto_eliminado", lambda e: self._safe(
            "productos", "producto_eliminado",
            lambda: f"Producto #{e.producto_id}",
        ))

        # ── Proveedores ──────────────────────────────────────────────
        # ProveedorModel usa emit(string, ...) → suscribir por string
        bus.subscribe("proveedor_guardado", lambda e: self._safe(
            "proveedores",
            "proveedor_creado" if e.es_nuevo else "proveedor_actualizado",
            lambda: f"{e.proveedor.nombre}",
        ))
        bus.subscribe("proveedor_eliminado", lambda e: self._safe(
            "proveedores", "proveedor_eliminado",
            lambda: f"Proveedor #{e.proveedor_id}",
        ))

        # ── Usuarios & Roles ─────────────────────────────────────────
        # UsuariosModel usa emit(string, ...) → suscribir por string
        bus.subscribe("usuario_guardado", lambda e: self._safe(
            "usuarios",
            "usuario_creado" if e.es_nuevo else "usuario_actualizado",
            lambda: f"@{e.usuario.username} ({e.usuario.nombre} {e.usuario.apellido})",
        ))
        bus.subscribe("usuario_eliminado", lambda e: self._safe(
            "usuarios", "usuario_eliminado",
            lambda: f"Usuario #{e.usuario_id}",
        ))
        bus.subscribe("rol_guardado", lambda e: self._safe(
            "usuarios",
            "rol_creado" if e.es_nuevo else "rol_actualizado",
            lambda: f"Rol: {e.rol.nombre}",
        ))
        bus.subscribe("rol_eliminado", lambda e: self._safe(
            "usuarios", "rol_eliminado",
            lambda: f"Rol #{e.rol_id}",
        ))

        # ── Facturación: impresión y PDF ────────────────────────────
        bus.subscribe(PDFGenerado, lambda e: self._safe(
            "facturacion", "pdf_generado",
            lambda: f"Factura #{e.factura_id} — {e.ruta_archivo}",
        ))
        bus.subscribe(ImpresionSolicitada, lambda e: self._safe(
            "facturacion", "impresion_solicitada",
            lambda: f"Factura #{e.factura_id}",
        ))

        # ── Sincronización DuckDB ────────────────────────────────────
        bus.subscribe(SincronizacionCompletada, lambda e: self._safe(
            "sync", "sync_completada",
            lambda: (
                f"{e.registros_enviados} registros en "
                f"{e.duracion_segundos:.1f}s"
            ),
        ))
        bus.subscribe(SincronizacionFallida, lambda e: self._safe(
            "sync", "sync_fallida",
            lambda: f"Error: {e.error}",
        ))
