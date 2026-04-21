"""
FacturacionModel

Rol: lógica de negocio del módulo de Facturación (cálculos, reglas).
No toca SQL directamente; delega persistencia en FacturaRepository.

El EventBus ahora soporta API dual: este módulo usa la forma por clase
(`publish(evento)` / `subscribe(Class, handler)`).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional

from core.db.sqlite_manager import SqliteManager
from core.db.migrations_runner import DEFAULT_DB_PATHS
from core.event_bus import EventBus
from events.facturacion_events import (
    FacturaCreada, FacturaAnulada, FacturaPagada,
    StockSolicitado, StockDescontado, StockInsuficiente,
    SincronizacionIniciada, SincronizacionCompletada, SincronizacionFallida,
)
from features.facturacion.repository import FacturaRepository


IVA_CR = 0.13

# Descargador histórico: función que dada (desde, hasta) devuelve las
# filas remotas listas para `FacturaRepository.volcar_historia_temp`.
# En Fase 3 la inyectará el SyncService contra MotherDuck.
HistorialDownloader = Callable[[datetime, datetime], list[dict]]


class FacturacionModel:
    """
    - Transacciones diarias → SQLite local (vía FacturaRepository).
    - Reportes analíticos   → DuckDB remoto (Fase 3: todavía no implementado).
    """

    def __init__(
        self,
        event_bus: EventBus,
        repository: Optional[FacturaRepository] = None,
        db_path: Optional[str] = None,
        historial_downloader: Optional[HistorialDownloader] = None,
    ):
        self._bus = event_bus
        if repository is not None:
            self._repo = repository
        else:
            path = db_path or DEFAULT_DB_PATHS["facturas"]
            self._repo = FacturaRepository(SqliteManager.get(path))
        self._historial_downloader = historial_downloader
        self._suscribir_eventos()

    def set_historial_downloader(self, downloader: Optional[HistorialDownloader]) -> None:
        """Inyecta el descargador de histórico (Fase 3 lo hará con MotherDuck)."""
        self._historial_downloader = downloader

    # ------------------------------------------------------------------
    # Suscripciones (API por clase del EventBus dual)
    # ------------------------------------------------------------------
    def _suscribir_eventos(self) -> None:
        self._bus.subscribe(StockDescontado, self._on_stock_descontado)
        self._bus.subscribe(StockInsuficiente, self._on_stock_insuficiente)

    # ------------------------------------------------------------------
    # Operaciones de negocio
    # ------------------------------------------------------------------
    def crear_factura(
        self,
        tipo: str,
        entidad_id: int,
        lineas: list[dict],
        descuento_global: float = 0.0,
        impuesto_pct: float = IVA_CR,
        cuotas: Optional[list[dict]] = None,
        es_electronica: bool = False,
    ) -> int:
        if tipo not in ("venta", "compra"):
            raise ValueError(f"Tipo de factura inválido: {tipo!r}")
        if not lineas:
            raise ValueError("Una factura requiere al menos una línea.")

        subtotal = sum(
            l["cantidad"] * l["precio_unitario"] - l.get("descuento_linea", 0)
            for l in lineas
        )
        base_gravable = subtotal - descuento_global
        impuesto = round(base_gravable * impuesto_pct, 2)
        total = round(base_gravable + impuesto, 2)

        factura_id = self._repo.crear_factura(
            tipo=tipo,
            entidad_id=entidad_id,
            subtotal=subtotal,
            descuento_global=descuento_global,
            impuesto=impuesto,
            total=total,
            lineas=lineas,
            cuotas=cuotas,
            es_electronica=es_electronica,
        )

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
        self._repo.anular_factura(factura_id)
        self._bus.publish(FacturaAnulada(factura_id=factura_id, motivo=motivo))

    def registrar_pago(
        self, factura_id: int, monto: float, metodo: str = "efectivo"
    ) -> None:
        self._repo.registrar_pago(factura_id, monto, metodo)
        self._bus.publish(FacturaPagada(factura_id=factura_id, monto_pagado=monto))

    def agregar_linea(self, factura_id: int, linea: dict) -> None:
        self._repo.agregar_linea(factura_id, linea)

    def obtener_factura(self, factura_id: int) -> Optional[dict]:
        return self._repo.obtener_factura(factura_id)

    def listar_facturas(
        self, tipo: Optional[str] = None, estado: Optional[str] = None
    ) -> list[dict]:
        return self._repo.listar_facturas(tipo=tipo, estado=estado)

    def listar_facturas_hoy(
        self, tipo: Optional[str] = None, estado: Optional[str] = None
    ) -> list[dict]:
        return self._repo.listar_hoy(tipo=tipo, estado=estado)

    # ------------------------------------------------------------------
    # Histórico (caché local poblada bajo demanda)
    # ------------------------------------------------------------------
    def cargar_historial(
        self,
        desde: date | datetime,
        hasta: date | datetime,
        refrescar: bool = False,
    ) -> list[dict]:
        """
        Devuelve facturas en el rango desde `facturas_historia_temp`.

        - Si hay `historial_downloader` inyectado y (la caché está vacía o
          `refrescar=True`), descarga desde el origen remoto y vuelca la
          caché antes de leer.
        - Si no hay downloader (Fase 3 todavía no implementada), devuelve lo
          que esté en caché — o lista vacía si nada se ha descargado aún.
        """
        d_ini = self._a_datetime(desde, inicio=True)
        d_fin = self._a_datetime(hasta, inicio=False)
        periodo_key = f"{d_ini.date().isoformat()}_{d_fin.date().isoformat()}"

        cached = self._repo.leer_historia_temp_por_rango(d_ini, d_fin)
        necesita_descarga = refrescar or not cached

        if necesita_descarga and self._historial_downloader is not None:
            registros = self._historial_downloader(d_ini, d_fin) or []
            self._repo.volcar_historia_temp(registros, periodo_key=periodo_key)
            cached = self._repo.leer_historia_temp_por_rango(d_ini, d_fin)

        return cached

    @staticmethod
    def _a_datetime(valor: date | datetime, inicio: bool) -> datetime:
        if isinstance(valor, datetime):
            return valor
        # date puro -> inicio/fin del día
        t = datetime.min.time() if inicio else datetime.max.time()
        return datetime.combine(valor, t)

    # ------------------------------------------------------------------
    # Reacciones a eventos de bodega
    # ------------------------------------------------------------------
    def _on_stock_descontado(self, evento: StockDescontado) -> None:
        # Nada que hacer por ahora; la confirmación de stock no modifica la factura.
        pass

    def _on_stock_insuficiente(self, evento: StockInsuficiente) -> None:
        self.anular_factura(
            evento.factura_id,
            motivo=(
                f"Stock insuficiente: producto {evento.producto_id} "
                f"(disponible: {evento.cantidad_disponible}, "
                f"solicitado: {evento.cantidad_solicitada})"
            ),
        )

    # ------------------------------------------------------------------
    # Sincronización con DuckDB (Fase 3)
    # ------------------------------------------------------------------
    def set_sync_service(self, svc: object) -> None:
        """Inyecta el SyncService. Se llama desde main.py al arrancar."""
        self._sync_service = svc

    def sincronizar_con_duckdb(self, desde: datetime, hasta: datetime) -> None:
        """
        Delega en el SyncService (si fue inyectado).
        Si no hay sync_service, publica 'fallida' para que la UI lo reporte.
        """
        svc = getattr(self, "_sync_service", None)
        if svc is None:
            self._bus.publish(SincronizacionIniciada(desde=desde, hasta=hasta))
            self._bus.publish(SincronizacionFallida(
                error="SyncService no inicializado.",
                reintentos=0,
            ))
            return
        # El SyncService publica Iniciada/Completada/Fallida por sí mismo.
        svc.push_pendientes(desde=desde, hasta=hasta)
        # Nota: SincronizacionCompletada se mantiene importado por retro-compat.
        _ = SincronizacionCompletada
