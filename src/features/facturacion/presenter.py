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
        super().__init__(model, view, event_bus)

    def _connect_events(self) -> None:
        self._conectar_view()
        self._suscribir_eventos()

    # ------------------------------------------------------------------
    # Conexión View → Presenter (señales de UI)
    # ------------------------------------------------------------------

    def _conectar_view(self) -> None:
        self.view.sig_crear_factura.connect(self._on_crear_factura)
        self.view.sig_anular_factura.connect(self._on_anular_factura)
        self.view.sig_registrar_pago.connect(self._on_registrar_pago)
        self.view.sig_agregar_linea.connect(self._on_agregar_linea)
        self.view.sig_exportar_pdf.connect(self._on_exportar_pdf)
        self.view.sig_imprimir.connect(self._on_imprimir)
        self.view.sig_sincronizar_duckdb.connect(self._on_sincronizar_duckdb)
        self.view.sig_cargar_facturas.connect(self._on_cargar_facturas)

    # ------------------------------------------------------------------
    # Suscripciones a EventBus (eventos de otros módulos)
    # ------------------------------------------------------------------

    def _suscribir_eventos(self) -> None:
        self.event_bus.subscribe(FacturaCreada, self._on_factura_creada)
        self.event_bus.subscribe(FacturaAnulada, self._on_factura_anulada)
        self.event_bus.subscribe(FacturaPagada, self._on_factura_pagada)
        self.event_bus.subscribe(StockInsuficiente, self._on_stock_insuficiente_ui)
        self.event_bus.subscribe(SincronizacionIniciada, self._on_sync_iniciada)
        self.event_bus.subscribe(SincronizacionCompletada, self._on_sync_completada)
        self.event_bus.subscribe(SincronizacionFallida, self._on_sync_fallida)

    # ------------------------------------------------------------------
    # Handlers de señales de la View
    # ------------------------------------------------------------------

    def _on_crear_factura(self, datos: dict) -> None:
        try:
            factura_id = self.model.crear_factura(
                tipo=datos["tipo"],
                entidad_id=datos["entidad_id"],
                lineas=datos["lineas"],
                descuento_global=datos.get("descuento_global", 0.0),
                impuesto_pct=datos.get("impuesto_pct", 0.13),
                cuotas=datos.get("cuotas"),
                es_electronica=datos.get("es_electronica", False),
            )
            self.view.mostrar_factura(self.model.obtener_factura(factura_id))
        except Exception as exc:
            self.view.mostrar_error(f"Error al crear factura: {exc}")

    def _on_anular_factura(self, factura_id: int, motivo: str) -> None:
        try:
            self.model.anular_factura(factura_id, motivo)
        except Exception as exc:
            self.view.mostrar_error(f"Error al anular factura: {exc}")

    def _on_registrar_pago(self, factura_id: int, monto: float, metodo: str) -> None:
        try:
            self.model.registrar_pago(factura_id, monto, metodo)
        except Exception as exc:
            self.view.mostrar_error(f"Error al registrar pago: {exc}")

    def _on_agregar_linea(self, factura_id: int, linea: dict) -> None:
        try:
            self.model.agregar_linea(factura_id, linea)
            self.view.mostrar_factura(self.model.obtener_factura(factura_id))
        except Exception as exc:
            self.view.mostrar_error(f"Error al agregar línea: {exc}")

    def _on_exportar_pdf(self, factura_id: int) -> None:
        # Por ahora solo notificamos la intención.
        # En una fase posterior se conectaría con un Generador de PDF.
        self.view.mostrar_info(f"Generando PDF para factura #{factura_id}...")
        self.event_bus.publish(PDFGenerado(factura_id=factura_id, ruta_archivo="pendiente"))

    def _on_imprimir(self, factura_id: int, impresora: object) -> None:
        # Placeholder para el servicio de impresión
        self.view.mostrar_info(f"Enviando factura #{factura_id} a la cola de impresión...")
        self.event_bus.publish(ImpresionSolicitada(factura_id=factura_id, impresora=str(impresora)))

    def _on_sincronizar_duckdb(self, desde, hasta) -> None:
        self.model.sincronizar_con_duckdb(desde, hasta)

    def _on_cargar_facturas(self, filtros: dict) -> None:
        facturas = self.model.listar_facturas(
            tipo=filtros.get("tipo"),
            estado=filtros.get("estado"),
        )
        self.view.cargar_tabla(facturas)

    # ------------------------------------------------------------------
    # Handlers de EventBus → View
    # ------------------------------------------------------------------

    def _on_factura_creada(self, evento: FacturaCreada) -> None:
        self.view.mostrar_info(
            f"Factura #{evento.factura_id} creada — Total: ₡{evento.total:,.2f}"
        )
        self._on_cargar_facturas({})

    def _on_factura_anulada(self, evento: FacturaAnulada) -> None:
        self.view.mostrar_advertencia(f"Factura #{evento.factura_id} anulada: {evento.motivo}")
        self._on_cargar_facturas({})

    def _on_factura_pagada(self, evento: FacturaPagada) -> None:
        self.view.mostrar_info(
            f"Pago registrado en factura #{evento.factura_id} — ₡{evento.monto_pagado:,.2f}"
        )

    def _on_stock_insuficiente_ui(self, evento: StockInsuficiente) -> None:
        self.view.mostrar_error(
            f"Stock insuficiente para producto #{evento.producto_id}. "
            f"Disponible: {evento.cantidad_disponible}, solicitado: {evento.cantidad_solicitada}. "
            f"La factura #{evento.factura_id} fue anulada."
        )

    def _on_sync_iniciada(self, evento: SincronizacionIniciada) -> None:
        self.view.mostrar_progreso("Sincronizando con servidor de análisis...")

    def _on_sync_completada(self, evento: SincronizacionCompletada) -> None:
        self.view.ocultar_progreso()
        self.view.mostrar_info(
            f"Sincronización completada: {evento.registros_enviados} registros "
            f"en {evento.duracion_segundos:.1f}s"
        )

    def _on_sync_fallida(self, evento: SincronizacionFallida) -> None:
        self.view.ocultar_progreso()
        self.view.mostrar_error(f"Error de sincronización: {evento.error}")