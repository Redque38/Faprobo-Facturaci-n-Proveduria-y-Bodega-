from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QFormLayout, QDialog, QDialogButtonBox, QMessageBox,
    QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from events.proveedor_events import (
    CargarProveedoresRequestedEvent,
    GuardarProveedorRequestedEvent,
    EliminarProveedorRequestedEvent,
    Proveedor,
)


# ═══════════════════════════════════════════════════════════
# Diálogo: Nuevo / Editar Proveedor
# ═══════════════════════════════════════════════════════════

class ProveedorDialog(QDialog):
    """Formulario modal para crear o editar un proveedor"""

    def __init__(self, parent=None, proveedor: Proveedor | None = None):
        super().__init__(parent)
        self.proveedor = proveedor
        es_edicion = proveedor is not None

        self.setWindowTitle("Editar Proveedor" if es_edicion else "Nuevo Proveedor")
        self.setMinimumWidth(420)
        self.setModal(True)

        self._apply_style()

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 25, 30, 25)

        # Título del diálogo
        title = QLabel("✏️ Editar Proveedor" if es_edicion else "➕ Nuevo Proveedor")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #bd93f9;")
        layout.addWidget(title)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #44475a;")
        layout.addWidget(sep)

        # Formulario
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.input_nombre    = self._make_input("Ej: TechComponents S.A.")
        self.input_contacto  = self._make_input("Nombre del contacto")
        self.input_telefono  = self._make_input("8888-0000")
        self.input_email     = self._make_input("correo@ejemplo.com")
        self.input_direccion = self._make_input("Provincia, Cantón, Detalle")

        form.addRow("Nombre *",    self.input_nombre)
        form.addRow("Contacto",    self.input_contacto)
        form.addRow("Teléfono",    self.input_telefono)
        form.addRow("Email",       self.input_email)
        form.addRow("Dirección",   self.input_direccion)

        layout.addLayout(form)

        # Pre-llenar si es edición
        if es_edicion:
            self.input_nombre.setText(proveedor.nombre)
            self.input_contacto.setText(proveedor.contacto)
            self.input_telefono.setText(proveedor.telefono)
            self.input_email.setText(proveedor.email)
            self.input_direccion.setText(proveedor.direccion)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("btnGuardar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_input(self, placeholder: str) -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(36)
        return inp

    def get_data(self) -> dict:
        return {
            "nombre":    self.input_nombre.text(),
            "contacto":  self.input_contacto.text(),
            "telefono":  self.input_telefono.text(),
            "email":     self.input_email.text(),
            "direccion": self.input_direccion.text(),
        }

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #282a36;
                color: #f8f8f2;
            }
            QLabel { color: #f8f8f2; font-size: 13px; }
            QLineEdit {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #bd93f9;
            }
            QDialogButtonBox QPushButton {
                background-color: #6272a4;
                color: #f8f8f2;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                min-width: 90px;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #7a8fc7;
            }
            QPushButton#btnGuardar {
                background-color: #50fa7b;
                color: #282a36;
                font-weight: bold;
            }
            QPushButton#btnGuardar:hover {
                background-color: #69ff92;
            }
        """)


# ═══════════════════════════════════════════════════════════
# Vista principal del módulo de Proveedores
# ═══════════════════════════════════════════════════════════

class ProveedoresView(QWidget):
    """Vista principal: barra de herramientas + tabla de proveedores"""

    COLUMNAS = ["ID", "Nombre", "Contacto", "Teléfono", "Email", "Dirección", "Acciones"]

    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self._proveedores: list[Proveedor] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Encabezado ──────────────────────────────────────
        header = QHBoxLayout()

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        lbl_title = QLabel("👥 Proveedores")
        lbl_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #bd93f9;")

        lbl_sub = QLabel("Gestión de proveedores y contactos")
        lbl_sub.setStyleSheet("color: #6272a4; font-size: 12px;")

        title_block.addWidget(lbl_title)
        title_block.addWidget(lbl_sub)

        self.btn_nuevo = QPushButton("➕  Nuevo Proveedor")
        self.btn_nuevo.setObjectName("btnNuevo")
        self.btn_nuevo.setFixedHeight(40)
        self.btn_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nuevo.clicked.connect(self._abrir_dialogo_nuevo)

        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍  Buscar proveedor...")
        self.input_buscar.setFixedHeight(40)
        self.input_buscar.setObjectName("inputBuscar")
        self.input_buscar.textChanged.connect(self._filtrar_tabla)

        header.addLayout(title_block)
        header.addStretch()
        header.addWidget(self.input_buscar)
        header.addSpacing(10)
        header.addWidget(self.btn_nuevo)

        layout.addLayout(header)

        # ── Separador ───────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #44475a;")
        layout.addWidget(sep)

        # ── Tabla ───────────────────────────────────────────
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(0, 50)
        self.tabla.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(6, 140)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(self.tabla)

        self._apply_style()

        # ── Suscripciones ────────────────────────────────────
        self.event_bus.subscribe("proveedores_cargados", self._on_proveedores_cargados)
        self.event_bus.subscribe("proveedor_guardado",   self._on_proveedor_guardado)
        self.event_bus.subscribe("proveedor_eliminado",  self._on_proveedor_eliminado)
        self.event_bus.subscribe("proveedor_error",      self._on_error)

    # ──────────────────────────────────────────────────────
    # Público: lo llama el Dashboard cuando activa la pestaña
    # ──────────────────────────────────────────────────────

    def cargar(self):
        """Solicita al model que cargue los proveedores"""
        self.event_bus.emit("cargar_proveedores_requested", CargarProveedoresRequestedEvent())

    # ──────────────────────────────────────────────────────
    # Handlers de eventos del EventBus
    # ──────────────────────────────────────────────────────

    def _on_proveedores_cargados(self, event):
        self._proveedores = event.proveedores
        self._renderizar_tabla(self._proveedores)

    def _on_proveedor_guardado(self, event):
        if event.es_nuevo:
            self._proveedores.append(event.proveedor)
        else:
            for i, p in enumerate(self._proveedores):
                if p.id == event.proveedor.id:
                    self._proveedores[i] = event.proveedor
                    break
        self._renderizar_tabla(self._proveedores)

    def _on_proveedor_eliminado(self, event):
        self._proveedores = [p for p in self._proveedores if p.id != event.proveedor_id]
        self._renderizar_tabla(self._proveedores)

    def _on_error(self, event):
        QMessageBox.warning(self, "Error", event.mensaje)

    # ──────────────────────────────────────────────────────
    # Renderizado de la tabla
    # ──────────────────────────────────────────────────────

    def _renderizar_tabla(self, proveedores: list[Proveedor]):
        self.tabla.setRowCount(0)
        for p in proveedores:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)

            datos = [str(p.id), p.nombre, p.contacto, p.telefono, p.email, p.direccion]
            for col, val in enumerate(datos):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.tabla.setItem(row, col, item)

            # Celda de Acciones
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(6, 4, 6, 4)
            cell_layout.setSpacing(6)

            btn_editar = QPushButton("✏️")
            btn_editar.setObjectName("btnAccion")
            btn_editar.setFixedSize(30, 30)
            btn_editar.setToolTip("Editar")
            btn_editar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_editar.clicked.connect(lambda _, prov=p: self._abrir_dialogo_editar(prov))

            btn_eliminar = QPushButton("🗑️")
            btn_eliminar.setObjectName("btnEliminar")
            btn_eliminar.setFixedSize(30, 30)
            btn_eliminar.setToolTip("Eliminar")
            btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_eliminar.clicked.connect(lambda _, prov=p: self._confirmar_eliminar(prov))

            cell_layout.addWidget(btn_editar)
            cell_layout.addWidget(btn_eliminar)
            self.tabla.setCellWidget(row, 6, cell_widget)

        self.tabla.setRowHeight(0, 44) if self.tabla.rowCount() > 0 else None
        for r in range(self.tabla.rowCount()):
            self.tabla.setRowHeight(r, 44)

    def _filtrar_tabla(self, texto: str):
        texto = texto.lower()
        filtrados = [
            p for p in self._proveedores
            if texto in p.nombre.lower()
            or texto in p.contacto.lower()
            or texto in p.email.lower()
        ]
        self._renderizar_tabla(filtrados)

    # ──────────────────────────────────────────────────────
    # Diálogos
    # ──────────────────────────────────────────────────────

    def _abrir_dialogo_nuevo(self):
        dlg = ProveedorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.event_bus.emit(
                "guardar_proveedor_requested",
                GuardarProveedorRequestedEvent(
                    proveedor_id=None,
                    nombre=data["nombre"],
                    contacto=data["contacto"],
                    telefono=data["telefono"],
                    email=data["email"],
                    direccion=data["direccion"],
                ),
            )

    def _abrir_dialogo_editar(self, proveedor: Proveedor):
        dlg = ProveedorDialog(self, proveedor=proveedor)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.event_bus.emit(
                "guardar_proveedor_requested",
                GuardarProveedorRequestedEvent(
                    proveedor_id=proveedor.id,
                    nombre=data["nombre"],
                    contacto=data["contacto"],
                    telefono=data["telefono"],
                    email=data["email"],
                    direccion=data["direccion"],
                ),
            )

    def _confirmar_eliminar(self, proveedor: Proveedor):
        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar a <b>{proveedor.nombre}</b>?<br>Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.event_bus.emit(
                "eliminar_proveedor_requested",
                EliminarProveedorRequestedEvent(proveedor_id=proveedor.id),
            )

    # ──────────────────────────────────────────────────────
    # Estilos Dracula
    # ──────────────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #282a36;
                color: #f8f8f2;
            }

            /* Botón Nuevo */
            QPushButton#btnNuevo {
                background-color: #50fa7b;
                color: #282a36;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
            }
            QPushButton#btnNuevo:hover {
                background-color: #69ff92;
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
                border: 1px solid #bd93f9;
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
                color: #bd93f9;
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

            /* Botones de acción en tabla */
            QPushButton#btnAccion {
                background-color: #6272a4;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton#btnAccion:hover {
                background-color: #7a8fc7;
            }
            QPushButton#btnEliminar {
                background-color: #3d1f1f;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton#btnEliminar:hover {
                background-color: #ff5555;
            }

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
