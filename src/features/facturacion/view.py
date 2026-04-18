from datetime import datetime
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QProgressBar, QComboBox,
    QDateEdit, QHeaderView
)
from core.event_bus import EventBus


class FacturacionView(QWidget):
    """
    Vista principal del módulo de facturación.
    Solo emite señales — sin lógica de negocio.
    """

    # Señales hacia el Presenter
    sig_crear_factura      = Signal(dict)
    sig_anular_factura     = Signal(int, str)
    sig_registrar_pago     = Signal(int, float, str)
    sig_agregar_linea      = Signal(int, dict)
    sig_exportar_pdf       = Signal(int)
    sig_imprimir           = Signal(int, object)       # (factura_id, impresora|None)
    sig_sincronizar_duckdb = Signal(object, object)    # (desde, hasta)
    sig_cargar_facturas    = Signal(dict)

    def __init__(self, event_bus: EventBus, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._bus = event_bus
        self._setup_ui()
        self._conectar_controles()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setWindowTitle("Facturación — Faprobo")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # --- Barra superior de filtros ---
        filtros = QHBoxLayout()
        self._cmb_tipo = QComboBox()
        self._cmb_tipo.addItems(["Todos", "venta", "compra"])
        self._cmb_estado = QComboBox()
        self._cmb_estado.addItems(["Todos", "pendiente", "pagada", "anulada"])
        self._btn_filtrar = QPushButton("Filtrar")
        self._btn_nueva   = QPushButton("+ Nueva factura")
        self._btn_nueva.setObjectName("primary")

        filtros.addWidget(QLabel("Tipo:"))
        filtros.addWidget(self._cmb_tipo)
        filtros.addWidget(QLabel("Estado:"))
        filtros.addWidget(self._cmb_estado)
        filtros.addWidget(self._btn_filtrar)
        filtros.addStretch()
        filtros.addWidget(self._btn_nueva)
        root.addLayout(filtros)

        # --- Tabla de facturas ---
        self._tabla = QTableWidget(0, 7)
        self._tabla.setHorizontalHeaderLabels([
            "ID", "Tipo", "Entidad", "Total ₡", "Impuesto ₡", "Estado", "Fecha",
        ])
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)
        root.addWidget(self._tabla)

        # --- Barra de acciones sobre factura seleccionada ---
        acciones = QHBoxLayout()
        self._btn_ver_pdf  = QPushButton("Exportar PDF")
        self._btn_imprimir = QPushButton("Imprimir")
        self._btn_pagar    = QPushButton("Registrar pago")
        self._btn_anular   = QPushButton("Anular")
        self._btn_anular.setObjectName("danger")
        acciones.addWidget(self._btn_ver_pdf)
        acciones.addWidget(self._btn_imprimir)
        acciones.addWidget(self._btn_pagar)
        acciones.addStretch()
        acciones.addWidget(self._btn_anular)
        root.addLayout(acciones)

        # --- Sección sincronización DuckDB ---
        sync_row = QHBoxLayout()
        self._date_desde = QDateEdit(datetime.now().date())
        self._date_hasta = QDateEdit(datetime.now().date())
        self._date_desde.setCalendarPopup(True)
        self._date_hasta.setCalendarPopup(True)
        self._btn_sync = QPushButton("Sincronizar analytics")
        sync_row.addWidget(QLabel("Sync desde:"))
        sync_row.addWidget(self._date_desde)
        sync_row.addWidget(QLabel("hasta:"))
        sync_row.addWidget(self._date_hasta)
        sync_row.addWidget(self._btn_sync)
        sync_row.addStretch()
        root.addLayout(sync_row)

        # --- Barra de progreso (oculta por defecto) ---
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # modo indeterminado
        self._progress.hide()
        root.addWidget(self._progress)

    def _conectar_controles(self) -> None:
        self._btn_filtrar.clicked.connect(self._emit_cargar_facturas)
        self._btn_nueva.clicked.connect(self._abrir_dialogo_nueva)
        self._btn_ver_pdf.clicked.connect(self._emit_exportar_pdf)
        self._btn_imprimir.clicked.connect(self._emit_imprimir)
        self._btn_pagar.clicked.connect(self._emit_pagar)
        self._btn_anular.clicked.connect(self._emit_anular)
        self._btn_sync.clicked.connect(self._emit_sincronizar)

    # ------------------------------------------------------------------
    # Emisores de señales
    # ------------------------------------------------------------------

    def _emit_cargar_facturas(self) -> None:
        tipo   = self._cmb_tipo.currentText()
        estado = self._cmb_estado.currentText()
        self.sig_cargar_facturas.emit({
            "tipo":   None if tipo   == "Todos" else tipo,
            "estado": None if estado == "Todos" else estado,
        })

    def _abrir_dialogo_nueva(self) -> None:
        from features.facturacion.dialogs import NuevaFacturaDialog
        dlg = NuevaFacturaDialog(self)
        if dlg.exec():
            self.sig_crear_factura.emit(dlg.datos())

    def _emit_exportar_pdf(self) -> None:
        fid = self._factura_seleccionada()
        if fid:
            self.sig_exportar_pdf.emit(fid)

    def _emit_imprimir(self) -> None:
        fid = self._factura_seleccionada()
        if fid:
            self.sig_imprimir.emit(fid, None)

    def _emit_pagar(self) -> None:
        fid = self._factura_seleccionada()
        if not fid:
            return
        from features.facturacion.dialogs import PagoDialog
        dlg = PagoDialog(self)
        if dlg.exec():
            self.sig_registrar_pago.emit(fid, dlg.monto(), dlg.metodo())

    def _emit_anular(self) -> None:
        fid = self._factura_seleccionada()
        if not fid:
            return
        resp = QMessageBox.question(
            self, "Anular factura",
            f"¿Seguro que desea anular la factura #{fid}?",
        )
        if resp == QMessageBox.Yes:
            self.sig_anular_factura.emit(fid, "Anulada por el usuario")

    def _emit_sincronizar(self) -> None:
        desde = datetime.combine(self._date_desde.date().toPython(), datetime.min.time())
        hasta = datetime.combine(self._date_hasta.date().toPython(), datetime.max.time())
        self.sig_sincronizar_duckdb.emit(desde, hasta)

    # ------------------------------------------------------------------
    # Métodos públicos llamados desde el Presenter
    # ------------------------------------------------------------------

    def cargar_tabla(self, facturas: list[dict]) -> None:
        self._tabla.setRowCount(0)
        for f in facturas:
            row = self._tabla.rowCount()
            self._tabla.insertRow(row)
            self._tabla.setItem(row, 0, QTableWidgetItem(str(f["id"])))
            self._tabla.setItem(row, 1, QTableWidgetItem(f["tipo"]))
            self._tabla.setItem(row, 2, QTableWidgetItem(str(f["entidad_id"])))
            self._tabla.setItem(row, 3, QTableWidgetItem(f"₡{f['total']:,.2f}"))
            self._tabla.setItem(row, 4, QTableWidgetItem(f"₡{f['impuesto']:,.2f}"))
            self._tabla.setItem(row, 5, QTableWidgetItem(f["estado"]))
            self._tabla.setItem(row, 6, QTableWidgetItem(f["fecha_creacion"]))

    def mostrar_factura(self, factura: Optional[dict]) -> None:
        if not factura:
            return
        self._emit_cargar_facturas()

    def mostrar_info(self, mensaje: str) -> None:
        QMessageBox.information(self, "Información", mensaje)

    def mostrar_advertencia(self, mensaje: str) -> None:
        QMessageBox.warning(self, "Advertencia", mensaje)

    def mostrar_error(self, mensaje: str) -> None:
        QMessageBox.critical(self, "Error", mensaje)

    def mostrar_progreso(self, texto: str = "") -> None:
        self._progress.setFormat(texto)
        self._progress.show()

    def ocultar_progreso(self) -> None:
        self._progress.hide()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _factura_seleccionada(self) -> Optional[int]:
        fila = self._tabla.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Selección", "Selecciona una factura primero.")
            return None
        return int(self._tabla.item(fila, 0).text())
