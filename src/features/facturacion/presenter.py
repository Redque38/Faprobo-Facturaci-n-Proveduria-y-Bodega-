from core.base_presenter import BasePresenter
from core.event_bus import EventBus
from events.facturacion_events import (
    FacturaCreada, FacturaAnulada, FacturaPagada,
    PDFGenerado, ImpresionSolicitada,
    SincronizacionIniciada, SincronizacionCompletada, SincronizacionFallida,
    StockInsuficiente,
)
from features.facturacion.model import FacturacionModel
from features.facturacion.view import FacturacionView


class FacturacionPresenter(BasePresenter):

    def __init__(self, model: FacturacionModel, view: FacturacionView, event_bus: EventBus):
        super().__init__(event_bus)
        self._model = model
        self._view = view
        self._conectar_view()
        self._suscribir_eventos()

    # ------------------------------------------------------------------
    # Conexión View → Presenter (señales de UI)
    # ------------------------------------------------------------------

    def _conectar_view(self) -> None:
        self._view.sig_crear_factura.connect(self._on_crear_factura)
        self._view.sig_anular_factura.connect(self._on_anular_factura)
        self._view.sig_registrar_pago.connect(self._on_registrar_pago)
        self._view.sig_agregar_linea.connect(self._on_agregar_linea)
        self._view.sig_exportar_pdf.connect(self._on_exportar_pdf)
        self._view.sig_imprimir.connect(self._on_imprimir)
        self._view.sig_sincronizar_duckdb.connect(self._on_sincronizar_duckdb)
        self._view.sig_cargar_facturas.connect(self._on_cargar_facturas)

    # ------------------------------------------------------------------
    # Suscripciones a EventBus (eventos de otros módulos)
    # ------------------------------------------------------------------

    def _suscribir_eventos(self) -> None:
        self._event_bus.subscribe(FacturaCreada, self._on_factura_creada)
        self._event_bus.subscribe(FacturaAnulada, self._on_factura_anulada)
        self._event_bus.subscribe(FacturaPagada, self._on_factura_pagada)
        self._event_bus.subscribe(StockInsuficiente, self._on_stock_insuficiente_ui)
        self._event_bus.subscribe(SincronizacionIniciada, self._on_sync_iniciada)
        self._event_bus.subscribe(SincronizacionCompletada, self._on_sync_completada)
        self._event_bus.subscribe(SincronizacionFallida, self._on_sync_fallida)

    # ------------------------------------------------------------------
    # Handlers de señales de la View
    # ------------------------------------------------------------------

    def _on_crear_factura(self, datos: dict) -> None:
        try:
            factura_id = self._model.crear_factura(
                tipo=datos["tipo"],
                entidad_id=datos["entidad_id"],
                lineas=datos["lineas"],
                descuento_global=datos.get("descuento_global", 0.0),
                impuesto_pct=datos.get("impuesto_pct", 0.13),
                cuotas=datos.get("cuotas"),
                es_electronica=datos.get("es_electronica", False),
            )
            self._view.mostrar_factura(self._model.obtener_factura(factura_id))
        except Exception as exc:
            self._view.mostrar_error(f"Error al crear factura: {exc}")

    def _on_anular_factura(self, factura_id: int, motivo: str) -> None:
        try:
            self._model.anular_factura(factura_id, motivo)
        except Exception as exc:
            self._view.mostrar_error(f"Error al anular factura: {exc}")

    def _on_registrar_pago(self, factura_id: int, monto: float, metodo: str) -> None:
        try:
            self._model.registrar_pago(factura_id, monto, metodo)
        except Exception as exc:
            self._view.mostrar_error(f"Error al registrar pago: {exc}")

    def _on_agregar_linea(self, factura_id: int, linea: dict) -> None:
        try:
            self._model.agregar_linea(factura_id, linea)
            self._view.mostrar_factura(self._model.obtener_factura(factura_id))
        except Exception as exc:
            self._view.mostrar_error(f"Error al agregar línea: {exc}")

    def _on_sincronizar_duckdb(self, desde, hasta) -> None:
        self._model.sincronizar_con_duckdb(desde, hasta)

    def _on_cargar_facturas(self, filtros: dict) -> None:
        facturas = self._model.listar_facturas(
            tipo=filtros.get("tipo"),
            estado=filtros.get("estado"),
        )
        self._view.cargar_tabla(facturas)

    # ------------------------------------------------------------------
    # Handlers de EventBus → View
    # ------------------------------------------------------------------

    def _on_factura_creada(self, evento: FacturaCreada) -> None:
        self._view.mostrar_info(
            f"Factura #{evento.factura_id} creada — Total: ₡{evento.total:,.2f}"
        )
        self._on_cargar_facturas({})

    def _on_factura_anulada(self, evento: FacturaAnulada) -> None:
        self._view.mostrar_advertencia(f"Factura #{evento.factura_id} anulada: {evento.motivo}")
        self._on_cargar_facturas({})

    def _on_factura_pagada(self, evento: FacturaPagada) -> None:
        self._view.mostrar_info(
            f"Pago registrado en factura #{evento.factura_id} — ₡{evento.monto_pagado:,.2f}"
        )

    def _on_stock_insuficiente_ui(self, evento: StockInsuficiente) -> None:
        self._view.mostrar_error(
            f"Stock insuficiente para producto #{evento.producto_id}. "
            f"Disponible: {evento.cantidad_disponible}, solicitado: {evento.cantidad_solicitada}. "
            f"La factura #{evento.factura_id} fue anulada."
        )

    def _on_sync_iniciada(self, evento: SincronizacionIniciada) -> None:
        self._view.mostrar_progreso("Sincronizando con servidor de análisis...")

    def _on_sync_completada(self, evento: SincronizacionCompletada) -> None:
        self._view.ocultar_progreso()
        self._view.mostrar_info(
            f"Sincronización completada: {evento.registros_enviados} registros "
            f"en {evento.duracion_segundos:.1f}s"
        )

    def _on_sync_fallida(self, evento: SincronizacionFallida) -> None:
        self._view.ocultar_progreso()
        self._view.mostrar_error(f"Error de sincronización: {evento.error}")