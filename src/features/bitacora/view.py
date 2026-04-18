"""
BitacoraView — Vista de solo lectura del registro de auditoría.

Características:
  - Filtros: rango de fechas, módulo, texto libre.
  - Paginación: 50 entradas por página.
  - Lectura directa sobre bitacora.db (síncrona, solo al abrir/refrescar).
  - Sin Presenter ni Model separados — la vista gestiona su propia lectura.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QComboBox, QDateEdit,
)

_PAGE_SIZE = 50

_MODULOS = [
    "Todos", "facturacion", "pos", "productos",
    "proveedores", "usuarios", "sync", "sistema",
]

_COLS = ["#", "Fecha y Hora", "Usuario", "Módulo", "Acción", "Descripción"]


class BitacoraView(QWidget):
    """Vista de auditoría — solo lectura, sin EventBus."""

    def __init__(self, db_path: str) -> None:
        super().__init__()
        self._db_path   = db_path
        self._page      = 0          # página actual (0-based)
        self._total     = 0          # total de filas con los filtros actuales

        self._build_ui()
        self._apply_style()

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Encabezado ───────────────────────────────────────────────────────
        header      = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        lbl_title = QLabel("📋 Bitácora")
        lbl_title.setStyleSheet(
            "color: #f1fa8c; font-size: 20pt; font-weight: bold;"
            " font-family: 'Segoe UI';"
        )
        lbl_sub = QLabel("Registro de auditoría — todas las acciones del sistema")
        lbl_sub.setStyleSheet("color: #6272a4; font-size: 12px;")

        title_block.addWidget(lbl_title)
        title_block.addWidget(lbl_sub)
        header.addLayout(title_block)
        header.addStretch()

        self._btn_refrescar = QPushButton("↻  Actualizar")
        self._btn_refrescar.setObjectName("btnRefrescar")
        self._btn_refrescar.setFixedHeight(40)
        self._btn_refrescar.clicked.connect(self._refrescar)
        header.addWidget(self._btn_refrescar)
        layout.addLayout(header)

        # ── Separador ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #44475a;")
        layout.addWidget(sep)

        # ── Fila de filtros ───────────────────────────────────────────────────
        filtros = QHBoxLayout()
        filtros.setSpacing(10)

        hoy = QDate.currentDate()

        lbl_desde = QLabel("Desde:")
        lbl_desde.setStyleSheet("color: #f8f8f2; font-size: 12px;")
        self._date_desde = QDateEdit(hoy.addDays(-7))
        self._date_desde.setCalendarPopup(True)
        self._date_desde.setDisplayFormat("yyyy-MM-dd")
        self._date_desde.setFixedHeight(36)

        lbl_hasta = QLabel("Hasta:")
        lbl_hasta.setStyleSheet("color: #f8f8f2; font-size: 12px;")
        self._date_hasta = QDateEdit(hoy)
        self._date_hasta.setCalendarPopup(True)
        self._date_hasta.setDisplayFormat("yyyy-MM-dd")
        self._date_hasta.setFixedHeight(36)

        lbl_mod = QLabel("Módulo:")
        lbl_mod.setStyleSheet("color: #f8f8f2; font-size: 12px;")
        self._cmb_modulo = QComboBox()
        self._cmb_modulo.addItems(_MODULOS)
        self._cmb_modulo.setFixedHeight(36)

        self._input_buscar = QLineEdit()
        self._input_buscar.setPlaceholderText("🔍  Buscar en acción o descripción...")
        self._input_buscar.setFixedHeight(36)
        self._input_buscar.setObjectName("inputBuscar")
        self._input_buscar.returnPressed.connect(self._refrescar)

        self._btn_filtrar = QPushButton("Filtrar")
        self._btn_filtrar.setObjectName("btnFiltrar")
        self._btn_filtrar.setFixedHeight(36)
        self._btn_filtrar.clicked.connect(self._refrescar)

        for w in (lbl_desde, self._date_desde,
                  lbl_hasta, self._date_hasta,
                  lbl_mod, self._cmb_modulo,
                  self._input_buscar, self._btn_filtrar):
            filtros.addWidget(w)
        filtros.addStretch()
        layout.addLayout(filtros)

        # ── Tabla ─────────────────────────────────────────────────────────────
        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Columnas de ancho fijo
        for col, w in [(0, 50), (1, 145), (2, 110), (3, 110), (4, 160)]:
            self._tabla.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.Fixed
            )
            self._tabla.setColumnWidth(col, w)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setShowGrid(False)
        self._tabla.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self._tabla, stretch=1)

        # ── Barra de paginación ───────────────────────────────────────────────
        pag = QHBoxLayout()
        pag.setSpacing(8)

        self._btn_prev = QPushButton("◀  Anterior")
        self._btn_prev.setObjectName("btnPag")
        self._btn_prev.setFixedHeight(34)
        self._btn_prev.clicked.connect(self._pagina_anterior)

        self._lbl_pagina = QLabel("Página 0 / 0  (0 entradas)")
        self._lbl_pagina.setStyleSheet("color: #6272a4; font-size: 12px;")
        self._lbl_pagina.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_next = QPushButton("Siguiente  ▶")
        self._btn_next.setObjectName("btnPag")
        self._btn_next.setFixedHeight(34)
        self._btn_next.clicked.connect(self._pagina_siguiente)

        pag.addWidget(self._btn_prev)
        pag.addStretch()
        pag.addWidget(self._lbl_pagina)
        pag.addStretch()
        pag.addWidget(self._btn_next)
        layout.addLayout(pag)

    # ── Carga de datos ────────────────────────────────────────────────────────

    def cargar(self) -> None:
        """Llamado por el Dashboard al navegar a esta sección."""
        self._page = 0
        self._cargar_pagina()

    def _refrescar(self) -> None:
        self._page = 0
        self._cargar_pagina()

    def _pagina_anterior(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._cargar_pagina()

    def _pagina_siguiente(self) -> None:
        total_paginas = max(1, (self._total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        if self._page < total_paginas - 1:
            self._page += 1
            self._cargar_pagina()

    def _cargar_pagina(self) -> None:
        """Lee N entradas de la página actual desde bitacora.db."""
        desde   = self._date_desde.date().toString("yyyy-MM-dd")
        hasta   = self._date_hasta.date().toString("yyyy-MM-dd") + " 23:59:59"
        modulo  = self._cmb_modulo.currentText()
        texto   = self._input_buscar.text().strip()

        where_clauses = ["timestamp BETWEEN ? AND ?"]
        params: list = [desde, hasta]

        if modulo != "Todos":
            where_clauses.append("modulo = ?")
            params.append(modulo)

        if texto:
            where_clauses.append("(LOWER(accion) LIKE LOWER(?) OR LOWER(descripcion) LIKE LOWER(?))")
            params.extend([f"%{texto}%", f"%{texto}%"])

        where = " AND ".join(where_clauses)

        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row

            # Contar total
            count_row = conn.execute(
                f"SELECT COUNT(*) FROM bitacora WHERE {where}", params
            ).fetchone()
            self._total = count_row[0] if count_row else 0

            # Cargar página
            offset = self._page * _PAGE_SIZE
            rows = conn.execute(
                f"SELECT id, timestamp, usuario_nom, modulo, accion, descripcion "
                f"FROM bitacora WHERE {where} "
                f"ORDER BY timestamp DESC "
                f"LIMIT {_PAGE_SIZE} OFFSET {offset}",
                params,
            ).fetchall()
            conn.close()

            self._renderizar(rows)

        except sqlite3.OperationalError:
            # La tabla aún no existe (primera ejecución antes del primer log)
            self._tabla.setRowCount(0)
            self._total = 0
            self._actualizar_paginacion()

    def _renderizar(self, rows) -> None:
        self._tabla.setRowCount(0)
        for row in rows:
            r = self._tabla.rowCount()
            self._tabla.insertRow(r)
            datos = [
                str(row["id"]),
                row["timestamp"],
                row["usuario_nom"],
                row["modulo"],
                row["accion"],
                row["descripcion"],
            ]
            for col, val in enumerate(datos):
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                # Color por módulo en la columna "Módulo"
                if col == 3:
                    item.setForeground(self._color_modulo(val))
                self._tabla.setItem(r, col, item)

        self._actualizar_paginacion()

    def _actualizar_paginacion(self) -> None:
        total_pag = max(1, (self._total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        pag_actual = self._page + 1
        self._lbl_pagina.setText(
            f"Página {pag_actual} / {total_pag}  ({self._total} entradas)"
        )
        self._btn_prev.setEnabled(self._page > 0)
        self._btn_next.setEnabled(self._page < total_pag - 1)

    # ── Colores por módulo ────────────────────────────────────────────────────

    @staticmethod
    def _color_modulo(modulo: str):
        from PySide6.QtGui import QColor
        colores = {
            "facturacion": QColor("#50fa7b"),
            "pos":         QColor("#ffb86c"),
            "productos":   QColor("#8be9fd"),
            "proveedores": QColor("#bd93f9"),
            "usuarios":    QColor("#ff79c6"),
            "sync":        QColor("#6272a4"),
            "sistema":     QColor("#f1fa8c"),
        }
        return colores.get(modulo, QColor("#f8f8f2"))

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
            QLineEdit#inputBuscar:focus { border: 1px solid #f1fa8c; }

            QPushButton#btnRefrescar {
                background-color: #44475a;
                color: #f1fa8c;
                border: 1px solid #f1fa8c;
                border-radius: 8px;
                padding: 6px 18px;
                font-size: 13px;
            }
            QPushButton#btnRefrescar:hover {
                background-color: #f1fa8c;
                color: #282a36;
            }

            QPushButton#btnFiltrar {
                background-color: #6272a4;
                color: #f8f8f2;
                border: none;
                border-radius: 6px;
                padding: 4px 16px;
                font-size: 13px;
            }
            QPushButton#btnFiltrar:hover { background-color: #7a8fc7; }

            QPushButton#btnPag {
                background-color: #44475a;
                color: #f8f8f2;
                border: none;
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 13px;
            }
            QPushButton#btnPag:hover    { background-color: #6272a4; }
            QPushButton#btnPag:disabled { color: #44475a; background-color: #282a36; }

            QComboBox {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 4px 10px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QComboBox:focus { border: 1px solid #f1fa8c; }
            QComboBox QAbstractItemView {
                background-color: #44475a;
                color: #f8f8f2;
                selection-background-color: #6272a4;
            }

            QDateEdit {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 4px 8px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QDateEdit:focus { border: 1px solid #f1fa8c; }

            QTableWidget {
                background-color: #1e1e2e;
                border: 1px solid #44475a;
                border-radius: 10px;
                gridline-color: transparent;
                font-size: 13px;
                color: #f8f8f2;
            }
            QTableWidget::item            { padding: 6px 8px; }
            QTableWidget::item:selected   { background-color: #44475a; }
            QTableWidget::item:alternate  { background-color: #252536; }
            QHeaderView::section {
                background-color: #282a36;
                color: #6272a4;
                font-size: 12px;
                border: none;
                border-bottom: 1px solid #44475a;
                padding: 6px 8px;
            }
        """)
