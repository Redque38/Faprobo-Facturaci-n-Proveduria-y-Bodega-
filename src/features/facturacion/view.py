from datetime import date, datetime, timedelta
from typing import Optional

from PySide6.QtCore import Signal, QDate, Qt

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QProgressBar, QComboBox,
    QDateEdit, QHeaderView, QFrame, QLineEdit
)

from core.event_bus import EventBus


# Constantes de UI para los selectores
ORIGEN_HOY       = "Facturas locales (SQLite)"
ORIGEN_HISTORIAL = "Historial (DuckDB)"

PERIODO_SEMANA     = "Última semana"
PERIODO_QUINCENA   = "Últimos 15 días"
PERIODO_MES        = "Último mes"
PERIODO_CUSTOM     = "Rango personalizado"


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
    sig_imprimir           = Signal(int, object)
    sig_sincronizar_duckdb = Signal(object, object)
    # Payload:
    #   { "origen": "sqlite"|"historial",
    #     "tipo": None|"venta"|"compra",
    #     "estado": None|"pendiente"|"pagada"|"anulada",
    #     "desde": datetime|None, "hasta": datetime|None,
    #     "refrescar": bool }
    sig_cargar_facturas    = Signal(dict)

    def __init__(self, event_bus: EventBus, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._bus = event_bus
        self._facturas_cache: list[dict] = []
        self._setup_ui()
        self._conectar_controles()
        self._apply_style()
        self._aplicar_visibilidad_periodo()
        # No emitimos aquí: el Presenter se encarga de la carga inicial
        # cuando conecta; así evitamos perder el evento si el presenter
        # aún no está suscrito.

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setWindowTitle("Facturación — Faprobo")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Encabezado ──────────────────────────────────────
        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        lbl_title = QLabel("🧾 Facturación")
        lbl_title.setStyleSheet(
            "color: #50fa7b; font-size: 20pt; font-weight: bold; font-family: 'Segoe UI';"
        )

        lbl_sub = QLabel("Gestión de facturas de venta y compra")
        lbl_sub.setStyleSheet("color: #6272a4; font-size: 12px;")

        title_block.addWidget(lbl_title)
        title_block.addWidget(lbl_sub)
        header.addLayout(title_block)
        header.addStretch()

        self._input_buscar = QLineEdit()
        self._input_buscar.setPlaceholderText("🔍  Buscar por ID, tipo, estado...")
        self._input_buscar.setFixedHeight(40)
        self._input_buscar.setObjectName("inputBuscar")
        self._input_buscar.textChanged.connect(self._filtrar_tabla)

        self._btn_nueva = QPushButton("➕  Nueva Factura")
        self._btn_nueva.setObjectName("primary")
        self._btn_nueva.setFixedHeight(40)
        self._btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(self._input_buscar)
        header.addSpacing(10)
        header.addWidget(self._btn_nueva)
        root.addLayout(header)

        # ── Separador ───────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #44475a;")
        root.addWidget(sep)

        # --- Fila 1: Origen + Período + Rango personalizado ---
        origen_row = QHBoxLayout()
        self._cmb_origen = QComboBox()
        self._cmb_origen.addItems([ORIGEN_HOY, ORIGEN_HISTORIAL])

        self._cmb_periodo = QComboBox()
        self._cmb_periodo.addItems([
            PERIODO_SEMANA, PERIODO_QUINCENA, PERIODO_MES, PERIODO_CUSTOM
        ])

        hoy = QDate.currentDate()
        self._date_desde = QDateEdit(hoy.addDays(-7))
        self._date_hasta = QDateEdit(hoy)
        for d in (self._date_desde, self._date_hasta):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")

        self._btn_refrescar = QPushButton("Refrescar histórico")
        self._btn_refrescar.setToolTip(
            "Vuelve a descargar desde el servidor analítico (DuckDB) "
            "y actualiza la caché local."
        )

        origen_row.addWidget(QLabel("Origen:"))
        origen_row.addWidget(self._cmb_origen)
        origen_row.addSpacing(12)
        origen_row.addWidget(QLabel("Período:"))
        origen_row.addWidget(self._cmb_periodo)
        origen_row.addWidget(QLabel("Desde:"))
        origen_row.addWidget(self._date_desde)
        origen_row.addWidget(QLabel("Hasta:"))
        origen_row.addWidget(self._date_hasta)
        origen_row.addWidget(self._btn_refrescar)
        origen_row.addStretch()
        root.addLayout(origen_row)

        # --- Fila 2: filtros por tipo/estado ---
        filtros = QHBoxLayout()
        self._cmb_tipo = QComboBox()
        self._cmb_tipo.addItems(["Todos", "venta", "compra"])
        self._cmb_estado = QComboBox()
        self._cmb_estado.addItems(["Todos", "pendiente", "pagada", "anulada"])
        self._btn_filtrar = QPushButton("Filtrar")

        filtros.addWidget(QLabel("Tipo:"))
        filtros.addWidget(self._cmb_tipo)
        filtros.addWidget(QLabel("Estado:"))
        filtros.addWidget(self._cmb_estado)
        filtros.addWidget(self._btn_filtrar)
        filtros.addStretch()
        root.addLayout(filtros)

        # --- Tabla de facturas ---
        self._tabla = QTableWidget(0, 7)
        self._tabla.setHorizontalHeaderLabels([
            "ID", "Tipo", "Entidad", "Total ₡", "Impuesto ₡", "Estado", "Fecha",
        ])
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setShowGrid(False)
        self._tabla.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        root.addWidget(self._tabla)

        # --- Etiqueta de estado / conteo ---
        self._lbl_resumen = QLabel("")
        self._lbl_resumen.setStyleSheet("color: #6272a4; font-size: 12px;")
        root.addWidget(self._lbl_resumen)

        # --- Barra de acciones ---
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

        # --- Sincronización DuckDB (se mantiene; Fase 3 lo hará funcional) ---
        sync_row = QHBoxLayout()
        self._btn_sync = QPushButton("Sincronizar analytics")
        sync_row.addWidget(self._btn_sync)
        sync_row.addStretch()
        root.addLayout(sync_row)

        # --- Barra de progreso ---
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.hide()
        root.addWidget(self._progress)

    def _conectar_controles(self) -> None:
        self._cmb_origen.currentTextChanged.connect(self._on_origen_cambio)
        self._cmb_periodo.currentTextChanged.connect(self._aplicar_visibilidad_periodo)
        self._btn_filtrar.clicked.connect(self._emit_cargar_facturas)
        self._btn_refrescar.clicked.connect(self._emit_cargar_facturas_refrescando)
        self._btn_nueva.clicked.connect(self._abrir_dialogo_nueva)
        self._btn_ver_pdf.clicked.connect(self._emit_exportar_pdf)
        self._btn_imprimir.clicked.connect(self._emit_imprimir)
        self._btn_pagar.clicked.connect(self._emit_pagar)
        self._btn_anular.clicked.connect(self._emit_anular)
        self._btn_sync.clicked.connect(self._emit_sincronizar)

    # ------------------------------------------------------------------
    # Lógica de visibilidad de controles de período
    # ------------------------------------------------------------------
    def _on_origen_cambio(self, _texto: str) -> None:
        self._aplicar_visibilidad_periodo()

    def _aplicar_visibilidad_periodo(self, *_args) -> None:
        historial = self._cmb_origen.currentText() == ORIGEN_HISTORIAL
        custom    = self._cmb_periodo.currentText() == PERIODO_CUSTOM

        self._cmb_periodo.setVisible(historial)
        self._btn_refrescar.setVisible(historial)

        # Las fechas solo tienen sentido en Historial + rango personalizado
        mostrar_fechas = historial and custom
        self._date_desde.setVisible(mostrar_fechas)
        self._date_hasta.setVisible(mostrar_fechas)
        for w in self.findChildren(QLabel):
            if w.text() in ("Desde:", "Hasta:"):
                w.setVisible(mostrar_fechas)

    # ------------------------------------------------------------------
    # Construcción del payload de carga
    # ------------------------------------------------------------------
    def _payload_cargar(self, *, refrescar: bool = False) -> dict:
        tipo   = self._cmb_tipo.currentText()
        estado = self._cmb_estado.currentText()
        origen = "sqlite" if self._cmb_origen.currentText() == ORIGEN_HOY else "historial"

        desde: Optional[datetime] = None
        hasta: Optional[datetime] = None
        if origen == "historial":
            desde, hasta = self._rango_segun_periodo()

        return {
            "origen":    origen,
            "tipo":      None if tipo   == "Todos" else tipo,
            "estado":    None if estado == "Todos" else estado,
            "desde":     desde,
            "hasta":     hasta,
            "refrescar": refrescar,
        }

    def _rango_segun_periodo(self) -> tuple[datetime, datetime]:
        periodo = self._cmb_periodo.currentText()
        hoy = date.today()
        if periodo == PERIODO_SEMANA:
            d_ini, d_fin = hoy - timedelta(days=7), hoy
        elif periodo == PERIODO_QUINCENA:
            d_ini, d_fin = hoy - timedelta(days=15), hoy
        elif periodo == PERIODO_MES:
            d_ini, d_fin = hoy - timedelta(days=30), hoy
        else:  # PERIODO_CUSTOM
            d_ini = self._date_desde.date().toPython()
            d_fin = self._date_hasta.date().toPython()
        return (
            datetime.combine(d_ini, datetime.min.time()),
            datetime.combine(d_fin, datetime.max.time()),
        )

    def _emit_cargar_facturas(self) -> None:
        self.sig_cargar_facturas.emit(self._payload_cargar(refrescar=False))

    def _emit_cargar_facturas_refrescando(self) -> None:
        self.sig_cargar_facturas.emit(self._payload_cargar(refrescar=True))

    def pedir_carga_inicial(self) -> None:
        """Llamado por el Presenter cuando ya está suscrito."""
        self._emit_cargar_facturas()

    # ------------------------------------------------------------------
    # Otros emisores
    # ------------------------------------------------------------------
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
        # Sincroniza todas las pendientes (Fase 3). Pasamos un rango
        # nominal como contrato; el SyncService real decidirá qué enviar.
        desde = datetime.combine(date.today(), datetime.min.time())
        hasta = datetime.combine(date.today(), datetime.max.time())
        self.sig_sincronizar_duckdb.emit(desde, hasta)

    # ------------------------------------------------------------------
    # Métodos públicos llamados desde el Presenter
    # ------------------------------------------------------------------
    def _filtrar_tabla(self, texto: str) -> None:
        texto = texto.lower().strip()
        if not texto:
            filtradas = self._facturas_cache
        else:
            filtradas = [
                f for f in self._facturas_cache
                if texto in str(f.get("id", "")).lower()
                or texto in str(f.get("tipo", "")).lower()
                or texto in str(f.get("estado", "")).lower()
            ]
        self._renderizar_tabla(filtradas)

    def _renderizar_tabla(self, facturas: list[dict]) -> None:
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
        self._lbl_resumen.setText(f"{len(facturas)} factura(s) listadas.")

    def cargar_tabla(self, facturas: list[dict]) -> None:
        self._facturas_cache = facturas
        self._renderizar_tabla(facturas)

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
    # Estilos Dracula
    # ------------------------------------------------------------------
    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: #282a36;
                color: #f8f8f2;
            }

            /* Botón principal (Nueva factura) */
            QPushButton#primary {
                background-color: #50fa7b;
                color: #282a36;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
            }
            QPushButton#primary:hover {
                background-color: #69ff92;
            }

            /* Botón peligroso (Anular) */
            QPushButton#danger {
                background-color: #3d1f1f;
                color: #ff5555;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #ff5555;
                border-radius: 8px;
                padding: 6px 18px;
            }
            QPushButton#danger:hover {
                background-color: #ff5555;
                color: #282a36;
            }

            /* Búsqueda */
            QLineEdit#inputBuscar {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 8px;
                padding: 0 12px;
                color: #f8f8f2;
                font-size: 13px;
                min-width: 220px;
            }
            QLineEdit#inputBuscar:focus {
                border: 1px solid #50fa7b;
            }

            /* Botones normales */
            QPushButton {
                background-color: #6272a4;
                color: #f8f8f2;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7a8fc7;
            }

            /* ComboBox */
            QComboBox {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 4px 10px;
                color: #f8f8f2;
                font-size: 13px;
                min-width: 120px;
            }
            QComboBox:focus {
                border: 1px solid #bd93f9;
            }
            QComboBox QAbstractItemView {
                background-color: #44475a;
                color: #f8f8f2;
                selection-background-color: #6272a4;
            }

            /* DateEdit */
            QDateEdit {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 4px 8px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QDateEdit:focus {
                border: 1px solid #bd93f9;
            }

            /* Labels */
            QLabel {
                color: #6272a4;
                font-size: 12px;
            }

            /* Tabla */
            QTableWidget {
                background-color: #1e1e2e;
                border: 1px solid #44475a;
                border-radius: 10px;
                gridline-color: transparent;
                font-size: 13px;
                selection-background-color: #44475a;
            }
            QTableWidget::item {
                padding: 6px 10px;
                color: #f8f8f2;
            }
            QTableWidget::item:alternate {
                background-color: #282a36;
            }
            QTableWidget::item:selected {
                background-color: #44475a;
                color: #50fa7b;
            }
            QHeaderView::section {
                background-color: #191927;
                color: #6272a4;
                font-weight: bold;
                font-size: 12px;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #44475a;
            }

            /* Barra de progreso */
            QProgressBar {
                background-color: #44475a;
                border: none;
                border-radius: 4px;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #bd93f9;
                border-radius: 4px;
            }

            /* Scrollbar */
            QScrollBar:vertical {
                background: #1e1e2e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #44475a;
                border-radius: 4px;
            }
        """)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _factura_seleccionada(self) -> Optional[int]:
        fila = self._tabla.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Selección", "Selecciona una factura primero.")
            return None
        return int(self._tabla.item(fila, 0).text())
