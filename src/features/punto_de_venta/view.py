"""
PosView — Vista del módulo Punto de Venta.

Arquitectura de la UI:
  PosView (QWidget)
  ├── Header (🛒 Punto de Venta + subtítulo)
  ├── Separador
  └── QTabWidget (_tabs)
      ├── TicketWidget [tab 0]   ← primera venta
      ├── TicketWidget [tab 1]   ← segunda venta en espera
      └── …
      [corner: "➕ Nueva Venta"]

TicketWidget (por tab):
  LEFT PANEL (stretch=3)          RIGHT PANEL (fixed 265px)
  ├── Barra búsqueda + btn        ├── Resumen (subtotal/dto/iva/total)
  ├── Tabla resultados            ├── Descuento global %
  ├── Separador                   ├── Método de pago
  └── Tabla carrito (con         ├── [🗑 Limpiar]
      spinboxes de cantidad       └── [✅ COBRAR]  ← desactivado si vacío
      y botones ✕ por fila)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from core.event_bus import EventBus

# ─── Constantes de columnas ───────────────────────────────────────────────────

_COLS_RES  = ["Código", "Nombre", "Precio ₡", "Stock", ""]
_COLS_CART = ["Código", "Producto", "Cant.", "P.Unit ₡", "Dto ₡", "Total ₡", ""]

_IVA = 0.13


# ═══════════════════════════════════════════════════════════════════════════════
# TicketWidget
# ═══════════════════════════════════════════════════════════════════════════════

class TicketWidget(QWidget):
    """
    Widget autónomo que representa una venta en curso.
    Cada tab del POS tiene su propia instancia — estado completamente independiente.
    """

    sig_buscar = Signal(str)                # (texto)
    sig_pagar  = Signal(list, float, str)   # (lineas, descuento_flat ₡, metodo)

    def __init__(self, ticket_id: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ticket_id         = ticket_id
        self._carrito: list[dict] = []

        self._build_ui()
        self._apply_style()

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(16)

        # ── PANEL IZQUIERDO ──────────────────────────────────────────────────
        left    = QWidget()
        lv      = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)

        # Búsqueda
        search_row = QHBoxLayout()
        self._input_buscar = QLineEdit()
        self._input_buscar.setPlaceholderText("🔍  Buscar producto por nombre o código...")
        self._input_buscar.setFixedHeight(40)
        self._input_buscar.setObjectName("inputBuscar")
        self._input_buscar.returnPressed.connect(self._on_buscar)

        self._btn_buscar = QPushButton("Buscar")
        self._btn_buscar.setFixedHeight(40)
        self._btn_buscar.setObjectName("btnSecondary")
        self._btn_buscar.clicked.connect(self._on_buscar)

        search_row.addWidget(self._input_buscar)
        search_row.addWidget(self._btn_buscar)
        lv.addLayout(search_row)

        # Resultados
        self._lbl_resultados = QLabel("Ingresá un término para buscar productos.")
        self._lbl_resultados.setStyleSheet("color: #6272a4; font-size: 12px;")
        lv.addWidget(self._lbl_resultados)

        self._tabla_res = QTableWidget(0, len(_COLS_RES))
        self._tabla_res.setHorizontalHeaderLabels(_COLS_RES)
        self._tabla_res.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla_res.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tabla_res.setColumnWidth(0, 95)
        self._tabla_res.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._tabla_res.setColumnWidth(2, 100)
        self._tabla_res.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._tabla_res.setColumnWidth(3, 60)
        self._tabla_res.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._tabla_res.setColumnWidth(4, 44)
        self._tabla_res.setFixedHeight(160)
        self._tabla_res.verticalHeader().setVisible(False)
        self._tabla_res.setShowGrid(False)
        self._tabla_res.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla_res.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla_res.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lv.addWidget(self._tabla_res)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #44475a;")
        lv.addWidget(sep)

        lbl_cart = QLabel("🛒  Ticket de Venta")
        lbl_cart.setStyleSheet(
            "color: #f8f8f2; font-size: 14px; font-weight: bold;"
        )
        lv.addWidget(lbl_cart)

        # Carrito
        self._tabla_cart = QTableWidget(0, len(_COLS_CART))
        self._tabla_cart.setHorizontalHeaderLabels(_COLS_CART)
        self._tabla_cart.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla_cart.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tabla_cart.setColumnWidth(0, 95)
        self._tabla_cart.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._tabla_cart.setColumnWidth(2, 72)
        self._tabla_cart.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._tabla_cart.setColumnWidth(3, 100)
        self._tabla_cart.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._tabla_cart.setColumnWidth(4, 80)
        self._tabla_cart.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._tabla_cart.setColumnWidth(5, 100)
        self._tabla_cart.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._tabla_cart.setColumnWidth(6, 38)
        self._tabla_cart.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla_cart.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla_cart.setAlternatingRowColors(True)
        self._tabla_cart.verticalHeader().setVisible(False)
        self._tabla_cart.setShowGrid(False)
        self._tabla_cart.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lv.addWidget(self._tabla_cart, stretch=1)

        outer.addWidget(left, stretch=3)

        # ── PANEL DERECHO ────────────────────────────────────────────────────
        right = QWidget()
        right.setFixedWidth(265)
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 0, 0, 0)
        rv.setSpacing(12)

        # Cuadro resumen
        summary = QFrame()
        summary.setObjectName("summaryFrame")
        sv = QVBoxLayout(summary)
        sv.setContentsMargins(16, 14, 16, 14)
        sv.setSpacing(6)

        self._lbl_subtotal  = QLabel("Subtotal:      ₡ 0.00")
        self._lbl_descuento = QLabel("Descuento:   ₡ 0.00")
        self._lbl_iva       = QLabel("IVA (13%):    ₡ 0.00")
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #44475a;")
        self._lbl_total = QLabel("TOTAL: ₡ 0.00")
        self._lbl_total.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: #50fa7b;"
        )
        for w in (self._lbl_subtotal, self._lbl_descuento,
                  self._lbl_iva, sep2, self._lbl_total):
            sv.addWidget(w)
        rv.addWidget(summary)

        # Descuento global %
        dto_row = QHBoxLayout()
        lbl_dto = QLabel("Descuento %:")
        lbl_dto.setStyleSheet("color: #f8f8f2; font-size: 12px;")
        self._spin_dto = QDoubleSpinBox()
        self._spin_dto.setRange(0, 100)
        self._spin_dto.setSuffix(" %")
        self._spin_dto.setDecimals(1)
        self._spin_dto.setFixedHeight(36)
        self._spin_dto.valueChanged.connect(self._actualizar_resumen)
        dto_row.addWidget(lbl_dto)
        dto_row.addWidget(self._spin_dto)
        rv.addLayout(dto_row)

        # Método de pago
        lbl_met = QLabel("Método de pago:")
        lbl_met.setStyleSheet("color: #f8f8f2; font-size: 12px;")
        self._cmb_metodo = QComboBox()
        self._cmb_metodo.addItems(["efectivo", "tarjeta", "sinpe"])
        self._cmb_metodo.setFixedHeight(36)
        rv.addWidget(lbl_met)
        rv.addWidget(self._cmb_metodo)

        rv.addStretch()

        # Botones de acción
        self._btn_limpiar = QPushButton("🗑   Limpiar ticket")
        self._btn_limpiar.setObjectName("btnLimpiar")
        self._btn_limpiar.setFixedHeight(40)
        self._btn_limpiar.clicked.connect(self._limpiar)

        self._btn_cobrar = QPushButton("✅   COBRAR")
        self._btn_cobrar.setObjectName("btnCobrar")
        self._btn_cobrar.setFixedHeight(52)
        self._btn_cobrar.setEnabled(False)   # se activa cuando hay productos
        self._btn_cobrar.clicked.connect(self._on_cobrar)

        rv.addWidget(self._btn_limpiar)
        rv.addWidget(self._btn_cobrar)

        outer.addWidget(right, stretch=0)

    # ── Lógica de búsqueda ───────────────────────────────────────────────────

    def _on_buscar(self) -> None:
        texto = self._input_buscar.text().strip()
        if texto:
            self.sig_buscar.emit(texto)

    def mostrar_resultados(self, productos: list[dict]) -> None:
        self._tabla_res.setRowCount(0)
        if not productos:
            self._lbl_resultados.setText("Sin resultados para esa búsqueda.")
            return

        self._lbl_resultados.setText(
            f"{len(productos)} producto(s) encontrado(s)."
        )
        for p in productos:
            row = self._tabla_res.rowCount()
            self._tabla_res.insertRow(row)
            for col, val in enumerate([
                p["codigo"],
                p["nombre"],
                f"₡ {p['precio_venta']:,.2f}",
                str(p["stock"]),
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                self._tabla_res.setItem(row, col, item)

            btn = QPushButton("➕")
            btn.setFixedSize(30, 28)
            btn.setObjectName("btnAccion")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if p["stock"] <= 0:
                btn.setEnabled(False)
                btn.setToolTip("Sin stock disponible")
            else:
                btn.setToolTip(f"Agregar '{p['nombre']}' al ticket")
                btn.clicked.connect(lambda _, prod=p: self._agregar(prod))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(4, 2, 4, 2)
            cl.addWidget(btn)
            self._tabla_res.setCellWidget(row, 4, cell)

    # ── Lógica del carrito ───────────────────────────────────────────────────

    def _agregar(self, producto: dict) -> None:
        """Agrega al carrito o incrementa la cantidad si ya existe."""
        for linea in self._carrito:
            if linea["producto_id"] == producto["id"]:
                linea["cantidad"] += 1
                self._renderizar_carrito()
                return
        self._carrito.append({
            "producto_id":    producto["id"],
            "codigo":         producto["codigo"],
            "descripcion":    producto["nombre"],
            "cantidad":       1,
            "precio_unitario": producto["precio_venta"],
            "descuento_linea": 0.0,
        })
        self._renderizar_carrito()

    def _renderizar_carrito(self) -> None:
        self._tabla_cart.setRowCount(0)

        for i, linea in enumerate(self._carrito):
            row = self._tabla_cart.rowCount()
            self._tabla_cart.insertRow(row)

            total_linea = (
                linea["cantidad"] * linea["precio_unitario"]
                - linea["descuento_linea"]
            )
            datos_texto = [
                linea["codigo"],
                linea["descripcion"],
                None,                              # col 2: spinbox widget
                f"₡ {linea['precio_unitario']:,.2f}",
                f"₡ {linea['descuento_linea']:,.2f}",
                f"₡ {total_linea:,.2f}",
                None,                              # col 6: botón ✕
            ]
            for col, val in enumerate(datos_texto):
                if val is None:
                    continue
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                self._tabla_cart.setItem(row, col, item)

            # QSpinBox para cantidad (col 2)
            spin = QSpinBox()
            spin.setMinimum(1)
            spin.setMaximum(9999)
            spin.setValue(linea["cantidad"])
            spin.setFixedWidth(64)
            spin.valueChanged.connect(
                lambda val, idx=i: self._cambiar_cantidad(idx, val)
            )
            spin_cell = QWidget()
            sc = QHBoxLayout(spin_cell)
            sc.setContentsMargins(4, 2, 4, 2)
            sc.addWidget(spin)
            self._tabla_cart.setCellWidget(row, 2, spin_cell)

            # Botón eliminar línea (col 6)
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(26, 26)
            btn_del.setObjectName("btnEliminar")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setToolTip("Quitar del ticket")
            btn_del.clicked.connect(lambda _, idx=i: self._eliminar(idx))
            del_cell = QWidget()
            dc = QHBoxLayout(del_cell)
            dc.setContentsMargins(4, 2, 4, 2)
            dc.addWidget(btn_del)
            self._tabla_cart.setCellWidget(row, 6, del_cell)

        self._actualizar_resumen()
        self._btn_cobrar.setEnabled(len(self._carrito) > 0)

    def _cambiar_cantidad(self, idx: int, valor: int) -> None:
        """Actualiza cantidad en el carrito y recalcula totales sin re-renderizar."""
        if 0 <= idx < len(self._carrito):
            self._carrito[idx]["cantidad"] = valor
            total_linea = (
                valor * self._carrito[idx]["precio_unitario"]
                - self._carrito[idx]["descuento_linea"]
            )
            item = QTableWidgetItem(f"₡ {total_linea:,.2f}")
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            )
            self._tabla_cart.setItem(idx, 5, item)
            self._actualizar_resumen()

    def _eliminar(self, idx: int) -> None:
        if 0 <= idx < len(self._carrito):
            self._carrito.pop(idx)
            self._renderizar_carrito()

    def _actualizar_resumen(self) -> None:
        subtotal = sum(
            l["cantidad"] * l["precio_unitario"] - l["descuento_linea"]
            for l in self._carrito
        )
        dto_pct  = self._spin_dto.value() / 100.0
        dto_flat = round(subtotal * dto_pct, 2)
        base     = subtotal - dto_flat
        iva      = round(base * _IVA, 2)
        total    = round(base + iva, 2)

        self._lbl_subtotal.setText( f"Subtotal:      ₡ {subtotal:>12,.2f}")
        self._lbl_descuento.setText(f"Descuento:   ₡ {dto_flat:>12,.2f}")
        self._lbl_iva.setText(      f"IVA (13%):    ₡ {iva:>12,.2f}")
        self._lbl_total.setText(    f"TOTAL: ₡ {total:,.2f}")

    def _limpiar(self) -> None:
        if not self._carrito:
            return
        if QMessageBox.question(
            self,
            "Limpiar ticket",
            "¿Eliminar todos los productos del ticket actual?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self._carrito.clear()
            self._renderizar_carrito()

    # ── Cobro ────────────────────────────────────────────────────────────────

    def _on_cobrar(self) -> None:
        if not self._carrito:
            return
        subtotal = sum(
            l["cantidad"] * l["precio_unitario"] - l["descuento_linea"]
            for l in self._carrito
        )
        dto_flat = round(subtotal * (self._spin_dto.value() / 100.0), 2)
        metodo   = self._cmb_metodo.currentText()
        self.sig_pagar.emit(list(self._carrito), dto_flat, metodo)

    # ── Respuestas del Presenter ──────────────────────────────────────────────

    def deshabilitar_cobrar(self) -> None:
        self._btn_cobrar.setEnabled(False)

    def habilitar_cobrar(self) -> None:
        self._btn_cobrar.setEnabled(len(self._carrito) > 0)

    def venta_completada(self, resultado: dict) -> None:
        """Imprime el ticket y limpia el carrito."""
        self._imprimir_ticket(resultado)

        # Limpiar estado
        self._carrito.clear()
        self._tabla_res.setRowCount(0)
        self._input_buscar.clear()
        self._spin_dto.setValue(0.0)
        self._lbl_resultados.setText("Ingresá un término para buscar productos.")
        self._renderizar_carrito()

        QMessageBox.information(
            self,
            "✅ Venta completada",
            f"Factura #{resultado['factura_id']} guardada exitosamente.\n"
            f"Total cobrado: ₡ {resultado['total']:,.2f}\n"
            f"Método: {resultado['metodo_pago']}",
        )

    # ── Impresión ────────────────────────────────────────────────────────────

    def _imprimir_ticket(self, resultado: dict) -> None:
        """Genera el HTML del ticket y abre el diálogo de impresión."""
        factura   = resultado.get("factura") or {}
        lineas    = resultado.get("lineas", [])
        total     = resultado.get("total", 0.0)
        metodo    = resultado.get("metodo_pago", "—")
        fid       = resultado.get("factura_id", "—")
        dto_flat  = resultado.get("descuento_global", 0.0)
        fecha_raw = factura.get("fecha_creacion", "")
        if not fecha_raw:
            fecha_raw = datetime.now().strftime("%Y-%m-%d %H:%M")

        subtotal = sum(
            l["cantidad"] * l["precio_unitario"] - l["descuento_linea"]
            for l in lineas
        )
        base = subtotal - dto_flat
        iva  = round(base * _IVA, 2)

        filas_html = "".join(
            f"<tr>"
            f"<td style='padding:4px 6px;'>{l['descripcion']}</td>"
            f"<td align='center' style='padding:4px 6px;'>{l['cantidad']}</td>"
            f"<td align='right'  style='padding:4px 6px;'>₡ {l['precio_unitario']:,.2f}</td>"
            f"<td align='right'  style='padding:4px 6px;'>"
            f"₡ {l['cantidad'] * l['precio_unitario'] - l['descuento_linea']:,.2f}</td>"
            f"</tr>"
            for l in lineas
        )

        html = f"""
        <html>
        <body style="font-family: 'Courier New', monospace; font-size: 11pt; margin: 20px;">
          <h2 style="text-align:center; margin-bottom:2px;">FAPROBO</h2>
          <p style="text-align:center; margin-top:2px;">
            Punto de Venta<br>
            <b>Factura #{fid}</b>&nbsp;&nbsp;|&nbsp;&nbsp;{fecha_raw}
          </p>
          <hr>
          <table width="100%" cellspacing="0" style="border-collapse:collapse;">
            <thead>
              <tr style="border-bottom:1px solid #000;">
                <th align="left"   style="padding:4px 6px;">Producto</th>
                <th align="center" style="padding:4px 6px;">Q</th>
                <th align="right"  style="padding:4px 6px;">P.Unit</th>
                <th align="right"  style="padding:4px 6px;">Total</th>
              </tr>
            </thead>
            <tbody>{filas_html}</tbody>
          </table>
          <hr>
          <table width="100%" style="margin-top:6px;">
            <tr><td>Subtotal:</td>
                <td align="right">₡ {subtotal:,.2f}</td></tr>
            <tr><td>Descuento:</td>
                <td align="right">₡ {dto_flat:,.2f}</td></tr>
            <tr><td>IVA (13%):</td>
                <td align="right">₡ {iva:,.2f}</td></tr>
            <tr style="border-top:1px solid #000;">
              <td><b>TOTAL:</b></td>
              <td align="right"><b>₡ {total:,.2f}</b></td>
            </tr>
            <tr><td>Método de pago:</td>
                <td align="right">{metodo}</td></tr>
          </table>
          <hr>
          <p style="text-align:center; margin-top:10px;">¡Gracias por su compra!</p>
        </body>
        </html>
        """

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)

    # ── Estilo Dracula ────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QWidget { background-color: #282a36; color: #f8f8f2; }

            QLineEdit#inputBuscar {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 8px;
                padding: 0 12px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QLineEdit#inputBuscar:focus { border: 1px solid #ffb86c; }

            QPushButton#btnSecondary {
                background-color: #6272a4;
                color: #f8f8f2;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
                font-size: 13px;
            }
            QPushButton#btnSecondary:hover { background-color: #7a8fc7; }

            QPushButton#btnCobrar {
                background-color: #50fa7b;
                color: #282a36;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton#btnCobrar:hover    { background-color: #69ff92; }
            QPushButton#btnCobrar:disabled {
                background-color: #44475a;
                color: #6272a4;
            }

            QPushButton#btnLimpiar {
                background-color: #3d1f1f;
                color: #ff5555;
                border: 1px solid #ff5555;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton#btnLimpiar:hover { background-color: #ff5555; color: #282a36; }

            QPushButton#btnAccion {
                background-color: #44475a;
                color: #8be9fd;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton#btnAccion:hover    { background-color: #6272a4; }
            QPushButton#btnAccion:disabled { color: #44475a; }

            QPushButton#btnEliminar {
                background-color: transparent;
                color: #ff5555;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnEliminar:hover { color: #ff79c6; }

            QFrame#summaryFrame {
                background-color: #1e1e2e;
                border: 1px solid #44475a;
                border-radius: 10px;
            }

            QTableWidget {
                background-color: #1e1e2e;
                border: 1px solid #44475a;
                border-radius: 8px;
                gridline-color: transparent;
                font-size: 13px;
                color: #f8f8f2;
            }
            QTableWidget::item { padding: 6px 8px; }
            QTableWidget::item:selected {
                background-color: #44475a;
                color: #f8f8f2;
            }
            QTableWidget::item:alternate { background-color: #252536; }
            QHeaderView::section {
                background-color: #282a36;
                color: #6272a4;
                font-size: 12px;
                border: none;
                border-bottom: 1px solid #44475a;
                padding: 6px 8px;
            }

            QComboBox {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 4px 10px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QComboBox:focus { border: 1px solid #bd93f9; }
            QComboBox QAbstractItemView {
                background-color: #44475a;
                color: #f8f8f2;
                selection-background-color: #6272a4;
            }

            QDoubleSpinBox, QSpinBox {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 4px 6px;
                color: #f8f8f2;
                font-size: 13px;
            }
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# PosView — contenedor principal con tabs
# ═══════════════════════════════════════════════════════════════════════════════

class PosView(QWidget):
    """Vista principal del Punto de Venta con soporte multi-ticket (ventas en espera)."""

    sig_buscar         = Signal(str, str)             # ticket_id, texto
    sig_procesar_venta = Signal(str, list, float, str) # ticket_id, lineas, dto_flat, metodo

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        self.event_bus        = event_bus
        self._ticket_counter  = 1
        self._tickets: dict[str, TicketWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Encabezado ───────────────────────────────────────────────────────
        header      = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        lbl_title = QLabel("🛒 Punto de Venta")
        lbl_title.setStyleSheet(
            "color: #ffb86c; font-size: 20pt; font-weight: bold; font-family: 'Segoe UI';"
        )
        lbl_sub = QLabel("Caja — ventas y cobros en mostrador")
        lbl_sub.setStyleSheet("color: #6272a4; font-size: 12px;")

        title_block.addWidget(lbl_title)
        title_block.addWidget(lbl_sub)
        header.addLayout(title_block)
        header.addStretch()
        layout.addLayout(header)

        # ── Separador ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #44475a;")
        layout.addWidget(sep)

        # ── TabWidget multi-ticket ────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self._cerrar_tab)

        # Botón "➕ Nueva Venta" como widget esquina del tab bar
        btn_nueva = QPushButton("➕  Nueva Venta")
        btn_nueva.setFixedHeight(34)
        btn_nueva.setStyleSheet(
            "QPushButton { background:#44475a; color:#f8f8f2; border:none; "
            "border-radius:6px; padding:4px 14px; font-size:13px; }"
            "QPushButton:hover { background:#6272a4; }"
        )
        btn_nueva.clicked.connect(self._nuevo_ticket)
        self._tabs.setCornerWidget(btn_nueva)

        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #44475a;
                border-radius: 8px;
                background-color: #282a36;
                padding: 4px;
            }
            QTabBar::tab {
                background-color: #1e1e2e;
                color: #6272a4;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                margin-right: 4px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #44475a;
                color: #ffb86c;
                font-weight: bold;
            }
            QTabBar::tab:hover { background-color: #2d2f3f; }
        """)

        layout.addWidget(self._tabs, stretch=1)

        # Crear el primer ticket automáticamente
        self._nuevo_ticket()

    # ── Gestión de tabs ───────────────────────────────────────────────────────

    def _nuevo_ticket(self) -> TicketWidget:
        ticket_id = f"t{uuid.uuid4().hex[:6]}"
        widget    = TicketWidget(ticket_id)

        # Conectar señales del TicketWidget hacia las señales agregadas del PosView
        widget.sig_buscar.connect(
            lambda texto, tid=ticket_id: self.sig_buscar.emit(tid, texto)
        )
        widget.sig_pagar.connect(
            lambda lineas, dto, met, tid=ticket_id:
                self.sig_procesar_venta.emit(tid, lineas, dto, met)
        )

        nombre = f"🧾 Venta #{self._ticket_counter}"
        self._ticket_counter += 1
        idx = self._tabs.addTab(widget, nombre)
        self._tabs.setCurrentIndex(idx)
        self._tickets[ticket_id] = widget
        return widget

    def _cerrar_tab(self, index: int) -> None:
        """Cierra el tab — no se puede cerrar si es el último."""
        if self._tabs.count() <= 1:
            QMessageBox.information(
                self, "Info", "Debe haber al menos un ticket activo."
            )
            return

        widget = self._tabs.widget(index)
        if isinstance(widget, TicketWidget) and widget._carrito:
            resp = QMessageBox.question(
                self,
                "¿Cerrar ticket?",
                "Este ticket tiene productos. ¿Cerrarlo de todas formas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp == QMessageBox.StandardButton.No:
                return

        if isinstance(widget, TicketWidget):
            self._tickets.pop(widget.ticket_id, None)
        self._tabs.removeTab(index)

    # ── API pública (llamada por el Presenter) ────────────────────────────────

    def mostrar_resultados(self, ticket_id: str, productos: list[dict]) -> None:
        widget = self._tickets.get(ticket_id)
        if widget:
            widget.mostrar_resultados(productos)

    def venta_completada(self, ticket_id: str, resultado: dict) -> None:
        widget = self._tickets.get(ticket_id)
        if widget:
            widget.venta_completada(resultado)

    def deshabilitar_cobrar(self, ticket_id: str) -> None:
        widget = self._tickets.get(ticket_id)
        if widget:
            widget.deshabilitar_cobrar()

    def habilitar_cobrar(self, ticket_id: str) -> None:
        widget = self._tickets.get(ticket_id)
        if widget:
            widget.habilitar_cobrar()

    def mostrar_error(self, mensaje: str) -> None:
        QMessageBox.critical(self, "Error — Punto de Venta", mensaje)
