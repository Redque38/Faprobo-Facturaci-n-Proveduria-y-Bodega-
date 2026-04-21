"""
PosModel — lógica de negocio del Punto de Venta.

Responsabilidades:
- Búsqueda de productos (via PosRepository sobre catalogo.db).
- Validación síncrona de stock antes de crear la factura.
- Delegación de creación de factura y registro de pago a FacturacionModel
  (único source of truth para facturas y stock).

El stock se descuenta a través del event FacturacionModel → StockSolicitado
→ StockDescontado (módulo bodega). Si el stock resulta insuficiente después
de la creación, el event StockInsuficiente anulará la factura automáticamente;
la vista lo captura vía el presenter.
"""
from __future__ import annotations

from core.event_bus import EventBus
from features.facturacion.model import FacturacionModel
from features.punto_de_venta.repository import PosRepository

IVA_CR = 0.13
CLIENTE_MOSTRADOR = 0   # entidad_id sin FK; se usa para ventas de mostrador


class PosModel:

    def __init__(
        self,
        event_bus: EventBus,
        repo: PosRepository,
        fact_model: FacturacionModel,
    ) -> None:
        self._bus  = event_bus
        self._repo = repo
        self._fact = fact_model

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------

    def buscar_productos(self, texto: str) -> list[dict]:
        """Devuelve productos activos con stock > 0 que coincidan con el texto."""
        if not texto.strip():
            return []
        return self._repo.buscar_productos(texto.strip())

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def validar_lineas(self, lineas: list[dict]) -> None:
        """
        Verifica stock disponible para cada línea del carrito.
        Lanza ValueError con mensaje descriptivo si alguna falla.
        """
        for linea in lineas:
            prod = self._repo.obtener_producto(linea["producto_id"])
            if prod is None or not prod.get("activo", 1):
                raise ValueError(
                    f"Producto '{linea['descripcion']}' no encontrado o inactivo."
                )
            if prod["stock"] < linea["cantidad"]:
                raise ValueError(
                    f"Stock insuficiente para '{prod['nombre']}'. "
                    f"Disponible: {prod['stock']}, "
                    f"solicitado: {int(linea['cantidad'])}."
                )

    # ------------------------------------------------------------------
    # Procesamiento de venta
    # ------------------------------------------------------------------

    def completar_venta(
        self,
        lineas: list[dict],
        descuento_global: float,
        metodo_pago: str,
    ) -> dict:
        """
        Flujo completo de una venta en caja:
          1. Valida stock de cada línea síncronamente.
          2. Crea la factura via FacturacionModel (publica FacturaCreada + StockSolicitado).
          3. Registra el pago para que la factura quede en estado 'pagada'.
          4. Retorna un dict con todos los datos para el ticket de impresión.

        Lanza ValueError si la validación falla antes de tocar la BD.
        """
        if not lineas:
            raise ValueError("El ticket está vacío.")

        # Validación previa de stock (falla rápido, antes de cualquier escritura)
        self.validar_lineas(lineas)

        # Crear factura (tipo venta, cliente mostrador)
        factura_id = self._fact.crear_factura(
            tipo="venta",
            entidad_id=CLIENTE_MOSTRADOR,
            lineas=lineas,
            descuento_global=descuento_global,   # monto plano en ₡
            impuesto_pct=IVA_CR,
        )

        # Obtener datos completos para el ticket
        factura = self._fact.obtener_factura(factura_id) or {}
        total   = factura.get("total", 0.0)

        # Registrar pago → factura pasa a estado 'pagada'
        self._fact.registrar_pago(factura_id, total, metodo_pago)

        return {
            "factura_id":      factura_id,
            "factura":         factura,
            "total":           total,
            "metodo_pago":     metodo_pago,
            "lineas":          lineas,
            "descuento_global": descuento_global,
        }
