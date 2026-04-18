"""
PosPresenter — conecta PosView con PosModel.
"""
from __future__ import annotations

from core.base_presenter import BasePresenter
from core.event_bus import EventBus
from events.facturacion_events import StockInsuficiente
from features.punto_de_venta.model import PosModel
from features.punto_de_venta.view import PosView


class PosPresenter(BasePresenter):

    def __init__(self, model: PosModel, view: PosView, event_bus: EventBus) -> None:
        super().__init__(model, view, event_bus)

    def _connect_events(self) -> None:
        # Señales de la View → Presenter
        self.view.sig_buscar.connect(self._on_buscar)
        self.view.sig_procesar_venta.connect(self._on_procesar_venta)

        # EventBus: si stock insuficiente la factura se anuló automáticamente
        self.event_bus.subscribe(StockInsuficiente, self._on_stock_insuficiente)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_buscar(self, ticket_id: str, texto: str) -> None:
        try:
            resultados = self.model.buscar_productos(texto)
            self.view.mostrar_resultados(ticket_id, resultados)
        except Exception as exc:
            self.view.mostrar_error(f"Error al buscar productos: {exc}")

    def _on_procesar_venta(
        self,
        ticket_id: str,
        lineas: list,
        descuento: float,
        metodo: str,
    ) -> None:
        try:
            self.view.deshabilitar_cobrar(ticket_id)
            resultado = self.model.completar_venta(lineas, descuento, metodo)
            self.view.venta_completada(ticket_id, resultado)
        except Exception as exc:
            self.view.habilitar_cobrar(ticket_id)
            self.view.mostrar_error(f"Error al procesar venta: {exc}")

    def _on_stock_insuficiente(self, evento: StockInsuficiente) -> None:
        self.view.mostrar_error(
            f"Stock insuficiente para el producto #{evento.producto_id}.\n"
            f"Disponible: {evento.cantidad_disponible}, "
            f"solicitado: {evento.cantidad_solicitada}.\n"
            f"La venta fue cancelada automáticamente."
        )
