from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QDoubleSpinBox,
    QSpinBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialogButtonBox
)
from PySide6.QtCore import Qt

class NuevaFacturaDialog(QDialog):
    """
    Diálogo para crear una nueva factura (venta o compra).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Factura")
        self.resize(600, 500)
        self._lineas = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Formulario básico
        form = QFormLayout()
        self._cmb_tipo = QComboBox()
        self._cmb_tipo.addItems(["venta", "compra"])

        self._txt_entidad = QSpinBox() # ID de cliente/proveedor por simplificar ahora
        self._txt_entidad.setRange(1, 100000)

        form.addRow("Tipo:", self._cmb_tipo)
        form.addRow("ID Entidad:", self._txt_entidad)
        layout.addLayout(form)

        # Tabla de líneas
        layout.addWidget(QLabel("Líneas de Detalle:"))
        self._tabla = QTableWidget(0, 4)
        self._tabla.setHorizontalHeaderLabels(["Producto ID", "Descripción", "Cant.", "Precio Unit."])
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self._tabla)

        # Controles para agregar línea
        add_layout = QHBoxLayout()
        self._spn_prod_id = QSpinBox()
        self._spn_prod_id.setRange(1, 10000)
        self._txt_desc = QLineEdit()
        self._txt_desc.setPlaceholderText("Descripción...")
        self._spn_cant = QDoubleSpinBox()
        self._spn_cant.setValue(1)
        self._spn_precio = QDoubleSpinBox()
        self._spn_precio.setRange(0, 9999999)

        btn_add = QPushButton("Agregar")
        btn_add.clicked.connect(self._agregar_linea_fila)

        add_layout.addWidget(self._spn_prod_id)
        add_layout.addWidget(self._txt_desc)
        add_layout.addWidget(self._spn_cant)
        add_layout.addWidget(self._spn_precio)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        # Botones de diálogo
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _agregar_linea_fila(self):
        row = self._tabla.rowCount()
        self._tabla.insertRow(row)
        self._tabla.setItem(row, 0, QTableWidgetItem(str(self._spn_prod_id.value())))
        self._tabla.setItem(row, 1, QTableWidgetItem(self._txt_desc.text()))
        self._tabla.setItem(row, 2, QTableWidgetItem(str(self._spn_cant.value())))
        self._tabla.setItem(row, 3, QTableWidgetItem(str(self._spn_precio.value())))

        self._lineas.append({
            "producto_id": self._spn_prod_id.value(),
            "descripcion": self._txt_desc.text(),
            "cantidad": self._spn_cant.value(),
            "precio_unitario": self._spn_precio.value()
        })

        # Limpiar
        self._txt_desc.clear()
        self._spn_cant.setValue(1)
        self._spn_precio.setValue(0)

    def datos(self) -> dict:
        return {
            "tipo": self._cmb_tipo.currentText(),
            "entidad_id": self._txt_entidad.value(),
            "lineas": self._lineas,
            "descuento_global": 0.0,
            "impuesto_pct": 0.13,
            "es_electronica": False
        }


class PagoDialog(QDialog):
    """
    Diálogo para registrar un pago.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Pago")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._spn_monto = QDoubleSpinBox()
        self._spn_monto.setRange(0, 99999999)
        self._cmb_metodo = QComboBox()
        self._cmb_metodo.addItems(["efectivo", "tarjeta", "transferencia", "sinpe"])

        form.addRow("Monto:", self._spn_monto)
        form.addRow("Método:", self._cmb_metodo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def monto(self) -> float:
        return self._spn_monto.value()

    def metodo(self) -> str:
        return self._cmb_metodo.currentText()
