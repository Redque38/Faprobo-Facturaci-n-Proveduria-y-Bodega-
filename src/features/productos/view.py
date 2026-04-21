from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QFormLayout, QDialog, QDialogButtonBox, QMessageBox,
    QFrame, QDoubleSpinBox, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from events.producto_events import (
    CargarProductosRequestedEvent,
    GuardarProductoRequestedEvent,
    EliminarProductoRequestedEvent,
    Producto,
)


# ═══════════════════════════════════════════════════════════
# Diálogo: Nuevo / Editar Producto
# ═══════════════════════════════════════════════════════════

class ProductoDialog(QDialog):
    """Formulario modal para crear o editar un producto"""

    def __init__(self, parent=None, producto: Producto | None = None):
        super().__init__(parent)
        self.producto = producto
        es_edicion = producto is not None

        self.setWindowTitle("Editar Producto" if es_edicion else "Nuevo Producto")
        self.setMinimumWidth(420)
        self.setModal(True)

        self._apply_style()

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 25, 30, 25)

        # Título del diálogo
        title = QLabel("✏️ Editar Producto" if es_edicion else "📦 Nuevo Producto")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #8be9fd;")
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

        self.input_codigo = self._make_input("Ej: P001")
        self.input_nombre = self._make_input("Nombre del producto")
        self.input_descripcion = self._make_input("Breve descripción")
        
        self.input_p_compra = QDoubleSpinBox()
        self.input_p_compra.setMaximum(9999999.0)
        self.input_p_compra.setPrefix("$ ")
        self.input_p_compra.setFixedHeight(36)
        
        self.input_p_venta = QDoubleSpinBox()
        self.input_p_venta.setMaximum(9999999.0)
        self.input_p_venta.setPrefix("$ ")
        self.input_p_venta.setFixedHeight(36)

        self.input_stock = QSpinBox()
        self.input_stock.setMaximum(999999)
        self.input_stock.setFixedHeight(36)

        self.input_categoria = self._make_input("Categoría")

        form.addRow("Código *",    self.input_codigo)
        form.addRow("Nombre *",    self.input_nombre)
        form.addRow("Descripción", self.input_descripcion)
        form.addRow("Precio Compra", self.input_p_compra)
        form.addRow("Precio Venta",  self.input_p_venta)
        form.addRow("Stock",       self.input_stock)
        form.addRow("Categoría",   self.input_categoria)

        layout.addLayout(form)

        # Pre-llenar si es edición
        if es_edicion:
            self.input_codigo.setText(producto.codigo)
            self.input_nombre.setText(producto.nombre)
            self.input_descripcion.setText(producto.descripcion)
            self.input_p_compra.setValue(producto.precio_compra)
            self.input_p_venta.setValue(producto.precio_venta)
            self.input_stock.setValue(producto.stock)
            self.input_categoria.setText(producto.categoria)

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
            "codigo":      self.input_codigo.text(),
            "nombre":      self.input_nombre.text(),
            "descripcion": self.input_descripcion.text(),
            "precio_compra": self.input_p_compra.value(),
            "precio_venta":  self.input_p_venta.value(),
            "stock":       self.input_stock.value(),
            "categoria":   self.input_categoria.text(),
        }

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #282a36;
                color: #f8f8f2;
            }
            QLabel { color: #f8f8f2; font-size: 13px; }
            QLineEdit, QDoubleSpinBox, QSpinBox {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
                border: 1px solid #8be9fd;
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
                background-color: #8be9fd;
                color: #282a36;
                font-weight: bold;
            }
            QPushButton#btnGuardar:hover {
                background-color: #a4ffff;
            }
        """)


# ═══════════════════════════════════════════════════════════
# Vista principal del módulo de Productos
# ═══════════════════════════════════════════════════════════

class ProductosView(QWidget):
    """Vista principal: barra de herramientas + tabla de productos"""

    COLUMNAS = ["ID", "Código", "Nombre", "P. Compra", "P. Venta", "Stock", "Categoría", "Acciones"]

    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self._productos: list[Producto] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Encabezado ──────────────────────────────────────
        header = QHBoxLayout()

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        lbl_title = QLabel("📦 Productos")
        lbl_title.setStyleSheet(
            "color: #8be9fd; font-size: 20pt; font-weight: bold; font-family: 'Segoe UI';"
        )

        lbl_sub = QLabel("Gestión de inventario y precios")
        lbl_sub.setStyleSheet("color: #6272a4; font-size: 12px;")

        title_block.addWidget(lbl_title)
        title_block.addWidget(lbl_sub)

        self.btn_nuevo = QPushButton("➕  Nuevo Producto")
        self.btn_nuevo.setObjectName("btnNuevo")
        self.btn_nuevo.setFixedHeight(40)
        self.btn_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nuevo.clicked.connect(self._abrir_dialogo_nuevo)

        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍  Buscar producto...")
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
        
        # Ajustes de ancho específicos
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(0, 50)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(1, 100)
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(3, 100)
        self.tabla.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(4, 100)
        self.tabla.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(5, 80)
        self.tabla.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(7, 100)
        
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(self.tabla)

        self._apply_style()

        # ── Suscripciones ────────────────────────────────────
        self.event_bus.subscribe("productos_cargados", self._on_productos_cargados)
        self.event_bus.subscribe("producto_guardado",   self._on_producto_guardado)
        self.event_bus.subscribe("producto_eliminado",  self._on_producto_eliminado)
        self.event_bus.subscribe("producto_error",      self._on_error)

    # ──────────────────────────────────────────────────────
    # Público: lo llama el Dashboard cuando activa la pestaña
    # ──────────────────────────────────────────────────────

    def cargar(self):
        """Solicita al model que cargue los productos"""
        self.event_bus.emit("cargar_productos_requested", CargarProductosRequestedEvent())

    # ──────────────────────────────────────────────────────
    # Handlers de eventos del EventBus
    # ──────────────────────────────────────────────────────

    def _on_productos_cargados(self, event):
        self._productos = event.productos
        self._renderizar_tabla(self._productos)

    def _on_producto_guardado(self, event):
        if event.es_nuevo:
            self._productos.append(event.producto)
        else:
            for i, p in enumerate(self._productos):
                if p.id == event.producto.id:
                    self._productos[i] = event.producto
                    break
        self._renderizar_tabla(self._productos)

    def _on_producto_eliminado(self, event):
        self._productos = [p for p in self._productos if p.id != event.producto_id]
        self._renderizar_tabla(self._productos)

    def _on_error(self, event):
        QMessageBox.warning(self, "Error", event.mensaje)

    # ──────────────────────────────────────────────────────
    # Renderizado de la tabla
    # ──────────────────────────────────────────────────────

    def _renderizar_tabla(self, productos: list[Producto]):
        self.tabla.setRowCount(0)
        for p in productos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)

            datos = [
                str(p.id), 
                p.codigo, 
                p.nombre, 
                f"${p.precio_compra:.2f}", 
                f"${p.precio_venta:.2f}", 
                str(p.stock), 
                p.categoria
            ]
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
            btn_editar.clicked.connect(lambda _, prod=p: self._abrir_dialogo_editar(prod))

            btn_eliminar = QPushButton("🗑️")
            btn_eliminar.setObjectName("btnEliminar")
            btn_eliminar.setFixedSize(30, 30)
            btn_eliminar.setToolTip("Eliminar")
            btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_eliminar.clicked.connect(lambda _, prod=p: self._confirmar_eliminar(prod))

            cell_layout.addWidget(btn_editar)
            cell_layout.addWidget(btn_eliminar)
            self.tabla.setCellWidget(row, 7, cell_widget)

        self.tabla.setRowHeight(0, 44) if self.tabla.rowCount() > 0 else None
        for r in range(self.tabla.rowCount()):
            self.tabla.setRowHeight(r, 44)

    def _filtrar_tabla(self, texto: str):
        texto = texto.lower()
        filtrados = [
            p for p in self._productos
            if texto in p.nombre.lower()
            or texto in p.codigo.lower()
            or texto in p.categoria.lower()
        ]
        self._renderizar_tabla(filtrados)

    # ──────────────────────────────────────────────────────
    # Diálogos
    # ──────────────────────────────────────────────────────

    def _abrir_dialogo_nuevo(self):
        dlg = ProductoDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.event_bus.emit(
                "guardar_producto_requested",
                GuardarProductoRequestedEvent(
                    producto_id=None,
                    codigo=data["codigo"],
                    nombre=data["nombre"],
                    descripcion=data["descripcion"],
                    precio_compra=data["precio_compra"],
                    precio_venta=data["precio_venta"],
                    stock=data["stock"],
                    categoria=data["categoria"],
                ),
            )

    def _abrir_dialogo_editar(self, producto: Producto):
        dlg = ProductoDialog(self, producto=producto)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.event_bus.emit(
                "guardar_producto_requested",
                GuardarProductoRequestedEvent(
                    producto_id=producto.id,
                    codigo=data["codigo"],
                    nombre=data["nombre"],
                    descripcion=data["descripcion"],
                    precio_compra=data["precio_compra"],
                    precio_venta=data["precio_venta"],
                    stock=data["stock"],
                    categoria=data["categoria"],
                ),
            )

    def _confirmar_eliminar(self, producto: Producto):
        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar el producto <b>{producto.nombre}</b>?<br>Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.event_bus.emit(
                "eliminar_producto_requested",
                EliminarProductoRequestedEvent(producto_id=producto.id),
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
                background-color: #8be9fd;
                color: #282a36;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
            }
            QPushButton#btnNuevo:hover {
                background-color: #a4ffff;
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
                border: 1px solid #8be9fd;
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
                color: #8be9fd;
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
