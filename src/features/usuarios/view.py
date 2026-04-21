"""
UsuariosView

Vista del módulo Usuarios & Roles.
Usa QTabWidget con dos tabs: Usuarios y Roles.
Aplica el estándar visual Dracula idéntico al de Proveedores/Productos.
"""
from __future__ import annotations

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QLineEdit, QTabWidget,
    QDialog, QFormLayout, QLineEdit as _QLineEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QMessageBox,
    QTextEdit,
)

from core.event_bus import EventBus
from events.usuario_events import (
    Usuario,
    Rol,
    CargarUsuariosRequestedEvent,
    CargarRolesRequestedEvent,
    GuardarUsuarioRequestedEvent,
    EliminarUsuarioRequestedEvent,
    GuardarRolRequestedEvent,
    EliminarRolRequestedEvent,
)


# ── Diálogo Usuario ───────────────────────────────────────────────────────────

class UsuarioDialog(QDialog):
    def __init__(self, parent: QWidget, roles: list[Rol], usuario: Usuario | None = None):
        super().__init__(parent)
        self._roles = roles
        self._usuario = usuario
        es_nuevo = usuario is None
        self.setWindowTitle("Nuevo Usuario" if es_nuevo else "Editar Usuario")
        self.setMinimumWidth(380)
        self._build_ui(es_nuevo)
        self._apply_style()

    def _build_ui(self, es_nuevo: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(8)

        self._txt_username = QLineEdit()
        self._txt_nombre   = QLineEdit()
        self._txt_apellido = QLineEdit()
        self._txt_password = QLineEdit()
        self._txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._cmb_rol = QComboBox()
        self._chk_activo = QCheckBox("Activo")
        self._chk_activo.setChecked(True)

        for r in self._roles:
            self._cmb_rol.addItem(r.nombre, userData=r.id)

        if self._usuario is not None:
            self._txt_username.setText(self._usuario.username)
            self._txt_nombre.setText(self._usuario.nombre)
            self._txt_apellido.setText(self._usuario.apellido)
            self._chk_activo.setChecked(self._usuario.activo)
            # Seleccionar rol actual
            idx = self._cmb_rol.findData(self._usuario.rol_id)
            if idx >= 0:
                self._cmb_rol.setCurrentIndex(idx)

        if not es_nuevo:
            self._txt_password.setPlaceholderText("Dejar vacío para no cambiar")

        form.addRow("Username:", self._txt_username)
        form.addRow("Nombre:", self._txt_nombre)
        form.addRow("Apellido:", self._txt_apellido)
        form.addRow("Contraseña:", self._txt_password)
        form.addRow("Rol:", self._cmb_rol)
        form.addRow("", self._chk_activo)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self) -> dict:
        return {
            "username": self._txt_username.text().strip(),
            "nombre":   self._txt_nombre.text().strip(),
            "apellido": self._txt_apellido.text().strip(),
            "password": self._txt_password.text(),
            "rol_id":   self._cmb_rol.currentData(),
            "activo":   self._chk_activo.isChecked(),
        }

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #282a36;
                color: #f8f8f2;
            }
            QLineEdit, QComboBox {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #ff79c6;
            }
            QComboBox QAbstractItemView {
                background-color: #44475a;
                color: #f8f8f2;
                selection-background-color: #6272a4;
            }
            QCheckBox {
                color: #f8f8f2;
                font-size: 13px;
            }
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
            QLabel {
                color: #f8f8f2;
                font-size: 13px;
            }
        """)


# ── Diálogo Rol ───────────────────────────────────────────────────────────────

class RolDialog(QDialog):
    def __init__(self, parent: QWidget, rol: Rol | None = None):
        super().__init__(parent)
        self._rol = rol
        es_nuevo = rol is None
        self.setWindowTitle("Nuevo Rol" if es_nuevo else "Editar Rol")
        self.setMinimumWidth(360)
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(8)

        self._txt_nombre      = QLineEdit()
        self._txt_descripcion = QTextEdit()
        self._txt_descripcion.setMaximumHeight(80)

        if self._rol is not None:
            self._txt_nombre.setText(self._rol.nombre)
            self._txt_descripcion.setPlainText(self._rol.descripcion)

        form.addRow("Nombre:", self._txt_nombre)
        form.addRow("Descripción:", self._txt_descripcion)
        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self) -> dict:
        return {
            "nombre":      self._txt_nombre.text().strip(),
            "descripcion": self._txt_descripcion.toPlainText().strip(),
        }

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #282a36;
                color: #f8f8f2;
            }
            QLineEdit, QTextEdit {
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8f8f2;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #ff79c6;
            }
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
            QLabel {
                color: #f8f8f2;
                font-size: 13px;
            }
        """)


# ── Vista principal ───────────────────────────────────────────────────────────

class UsuariosView(QWidget):
    """Vista principal del módulo Usuarios & Roles."""

    COLS_USUARIOS = ["ID", "Username", "Nombre", "Apellido", "Rol", "Estado", "Acciones"]
    COLS_ROLES    = ["ID", "Nombre", "Descripción", "Usuarios", "Estado", "Acciones"]

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.event_bus = event_bus
        self._usuarios: list[Usuario] = []
        self._roles: list[Rol] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Encabezado ──────────────────────────────────────
        header = QHBoxLayout()

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        lbl_title = QLabel("👤 Usuarios & Roles")
        lbl_title.setStyleSheet(
            "color: #ff79c6; font-size: 20pt; font-weight: bold; font-family: 'Segoe UI';"
        )

        lbl_sub = QLabel("Gestión de accesos y permisos del sistema")
        lbl_sub.setStyleSheet("color: #6272a4; font-size: 12px;")

        title_block.addWidget(lbl_title)
        title_block.addWidget(lbl_sub)
        header.addLayout(title_block)
        header.addStretch()

        layout.addLayout(header)

        # ── Separador ───────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #44475a;")
        layout.addWidget(sep)

        # ── Tabs ─────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setObjectName("usuariosTabs")

        # Tab Usuarios
        self._tab_usuarios = QWidget()
        self._build_tab_usuarios()
        self._tabs.addTab(self._tab_usuarios, "👤 Usuarios")

        # Tab Roles
        self._tab_roles = QWidget()
        self._build_tab_roles()
        self._tabs.addTab(self._tab_roles, "🔑 Roles")

        layout.addWidget(self._tabs)

        self._apply_style()

        # ── Suscripciones ────────────────────────────────────
        self.event_bus.subscribe("usuarios_cargados",  self._on_usuarios_cargados)
        self.event_bus.subscribe("roles_cargados",     self._on_roles_cargados)
        self.event_bus.subscribe("usuario_guardado",   self._on_usuario_guardado)
        self.event_bus.subscribe("usuario_eliminado",  self._on_usuario_eliminado)
        self.event_bus.subscribe("rol_guardado",       self._on_rol_guardado)
        self.event_bus.subscribe("rol_eliminado",      self._on_rol_eliminado)
        self.event_bus.subscribe("usuario_error",      self._on_error)

    # ── Construcción de tabs ──────────────────────────────────────────────────

    def _build_tab_usuarios(self) -> None:
        v = QVBoxLayout(self._tab_usuarios)
        v.setContentsMargins(0, 12, 0, 0)
        v.setSpacing(10)

        # Barra de herramientas
        bar = QHBoxLayout()
        self._input_buscar_usuarios = QLineEdit()
        self._input_buscar_usuarios.setPlaceholderText("🔍  Buscar usuario...")
        self._input_buscar_usuarios.setFixedHeight(40)
        self._input_buscar_usuarios.setObjectName("inputBuscar")
        self._input_buscar_usuarios.textChanged.connect(self._filtrar_usuarios)

        self._btn_nuevo_usuario = QPushButton("➕ Nuevo Usuario")
        self._btn_nuevo_usuario.setObjectName("btnNuevo")
        self._btn_nuevo_usuario.setFixedHeight(40)
        self._btn_nuevo_usuario.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_nuevo_usuario.clicked.connect(self._abrir_dialogo_nuevo_usuario)

        bar.addWidget(self._input_buscar_usuarios)
        bar.addSpacing(10)
        bar.addWidget(self._btn_nuevo_usuario)
        v.addLayout(bar)

        # Tabla
        self._tabla_usuarios = QTableWidget()
        self._tabla_usuarios.setColumnCount(len(self.COLS_USUARIOS))
        self._tabla_usuarios.setHorizontalHeaderLabels(self.COLS_USUARIOS)
        self._tabla_usuarios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla_usuarios.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tabla_usuarios.setColumnWidth(0, 50)
        self._tabla_usuarios.horizontalHeader().setSectionResizeMode(
            len(self.COLS_USUARIOS) - 1, QHeaderView.ResizeMode.Fixed
        )
        self._tabla_usuarios.setColumnWidth(len(self.COLS_USUARIOS) - 1, 140)
        self._tabla_usuarios.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla_usuarios.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla_usuarios.setAlternatingRowColors(True)
        self._tabla_usuarios.verticalHeader().setVisible(False)
        self._tabla_usuarios.setShowGrid(False)
        self._tabla_usuarios.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        v.addWidget(self._tabla_usuarios)

    def _build_tab_roles(self) -> None:
        v = QVBoxLayout(self._tab_roles)
        v.setContentsMargins(0, 12, 0, 0)
        v.setSpacing(10)

        # Barra de herramientas
        bar = QHBoxLayout()
        bar.addStretch()
        self._btn_nuevo_rol = QPushButton("➕ Nuevo Rol")
        self._btn_nuevo_rol.setObjectName("btnNuevo")
        self._btn_nuevo_rol.setFixedHeight(40)
        self._btn_nuevo_rol.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_nuevo_rol.clicked.connect(self._abrir_dialogo_nuevo_rol)
        bar.addWidget(self._btn_nuevo_rol)
        v.addLayout(bar)

        # Tabla
        self._tabla_roles = QTableWidget()
        self._tabla_roles.setColumnCount(len(self.COLS_ROLES))
        self._tabla_roles.setHorizontalHeaderLabels(self.COLS_ROLES)
        self._tabla_roles.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla_roles.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tabla_roles.setColumnWidth(0, 50)
        self._tabla_roles.horizontalHeader().setSectionResizeMode(
            len(self.COLS_ROLES) - 1, QHeaderView.ResizeMode.Fixed
        )
        self._tabla_roles.setColumnWidth(len(self.COLS_ROLES) - 1, 140)
        self._tabla_roles.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla_roles.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla_roles.setAlternatingRowColors(True)
        self._tabla_roles.verticalHeader().setVisible(False)
        self._tabla_roles.setShowGrid(False)
        self._tabla_roles.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        v.addWidget(self._tabla_roles)

    # ── Público ───────────────────────────────────────────────────────────────

    def cargar(self) -> None:
        """Solicita la carga de usuarios y roles al Model."""
        self.event_bus.emit("cargar_usuarios_requested", CargarUsuariosRequestedEvent())
        self.event_bus.emit("cargar_roles_requested",    CargarRolesRequestedEvent())

    # ── Handlers de EventBus ──────────────────────────────────────────────────

    def _on_usuarios_cargados(self, event) -> None:
        self._usuarios = event.usuarios
        self._renderizar_usuarios(self._usuarios)

    def _on_roles_cargados(self, event) -> None:
        self._roles = event.roles
        self._renderizar_roles(self._roles)

    def _on_usuario_guardado(self, event) -> None:
        if event.es_nuevo:
            self._usuarios.append(event.usuario)
        else:
            for i, u in enumerate(self._usuarios):
                if u.id == event.usuario.id:
                    self._usuarios[i] = event.usuario
                    break
        self._renderizar_usuarios(self._usuarios)

    def _on_usuario_eliminado(self, event) -> None:
        self._usuarios = [u for u in self._usuarios if u.id != event.usuario_id]
        self._renderizar_usuarios(self._usuarios)

    def _on_rol_guardado(self, event) -> None:
        if event.es_nuevo:
            self._roles.append(event.rol)
        else:
            for i, r in enumerate(self._roles):
                if r.id == event.rol.id:
                    self._roles[i] = event.rol
                    break
        self._renderizar_roles(self._roles)

    def _on_rol_eliminado(self, event) -> None:
        self._roles = [r for r in self._roles if r.id != event.rol_id]
        self._renderizar_roles(self._roles)

    def _on_error(self, event) -> None:
        QMessageBox.warning(self, "Error", event.mensaje)

    # ── Renderizado ───────────────────────────────────────────────────────────

    def _renderizar_usuarios(self, usuarios: list[Usuario]) -> None:
        self._tabla_usuarios.setRowCount(0)
        for u in usuarios:
            row = self._tabla_usuarios.rowCount()
            self._tabla_usuarios.insertRow(row)
            datos = [
                str(u.id),
                u.username,
                u.nombre,
                u.apellido,
                u.rol_nombre,
                "Activo" if u.activo else "Inactivo",
            ]
            for col, val in enumerate(datos):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._tabla_usuarios.setItem(row, col, item)

            # Celda de acciones
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(6, 4, 6, 4)
            cl.setSpacing(6)

            btn_editar = QPushButton("✏️")
            btn_editar.setObjectName("btnAccion")
            btn_editar.setFixedSize(30, 30)
            btn_editar.setToolTip("Editar")
            btn_editar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_editar.clicked.connect(lambda _, usr=u: self._abrir_dialogo_editar_usuario(usr))

            btn_eliminar = QPushButton("🗑️")
            btn_eliminar.setObjectName("btnEliminar")
            btn_eliminar.setFixedSize(30, 30)
            btn_eliminar.setToolTip("Eliminar")
            btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_eliminar.clicked.connect(lambda _, usr=u: self._confirmar_eliminar_usuario(usr))

            cl.addWidget(btn_editar)
            cl.addWidget(btn_eliminar)
            self._tabla_usuarios.setCellWidget(row, 6, cell)

        for r in range(self._tabla_usuarios.rowCount()):
            self._tabla_usuarios.setRowHeight(r, 44)

    def _renderizar_roles(self, roles: list[Rol]) -> None:
        self._tabla_roles.setRowCount(0)
        for r in roles:
            row = self._tabla_roles.rowCount()
            self._tabla_roles.insertRow(row)

            # Contar usuarios con este rol
            n_usuarios = sum(1 for u in self._usuarios if u.rol_id == r.id)

            datos = [
                str(r.id),
                r.nombre,
                r.descripcion,
                str(n_usuarios),
                "Activo" if r.activo else "Inactivo",
            ]
            for col, val in enumerate(datos):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._tabla_roles.setItem(row, col, item)

            # Celda de acciones
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(6, 4, 6, 4)
            cl.setSpacing(6)

            btn_editar = QPushButton("✏️")
            btn_editar.setObjectName("btnAccion")
            btn_editar.setFixedSize(30, 30)
            btn_editar.setToolTip("Editar")
            btn_editar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_editar.clicked.connect(lambda _, rol=r: self._abrir_dialogo_editar_rol(rol))

            btn_eliminar = QPushButton("🗑️")
            btn_eliminar.setObjectName("btnEliminar")
            btn_eliminar.setFixedSize(30, 30)
            btn_eliminar.setToolTip("Eliminar")
            btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_eliminar.clicked.connect(lambda _, rol=r: self._confirmar_eliminar_rol(rol))

            cl.addWidget(btn_editar)
            cl.addWidget(btn_eliminar)
            self._tabla_roles.setCellWidget(row, 5, cell)

        for r in range(self._tabla_roles.rowCount()):
            self._tabla_roles.setRowHeight(r, 44)

    # ── Filtrado ──────────────────────────────────────────────────────────────

    def _filtrar_usuarios(self, texto: str) -> None:
        texto = texto.lower()
        filtrados = [
            u for u in self._usuarios
            if texto in u.username.lower()
            or texto in u.nombre.lower()
            or texto in u.apellido.lower()
            or texto in u.rol_nombre.lower()
        ]
        self._renderizar_usuarios(filtrados)

    # ── Diálogos Usuarios ─────────────────────────────────────────────────────

    def _abrir_dialogo_nuevo_usuario(self) -> None:
        dlg = UsuarioDialog(self, roles=self._roles)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.event_bus.emit(
                "guardar_usuario_requested",
                GuardarUsuarioRequestedEvent(
                    usuario_id=None,
                    username=data["username"],
                    nombre=data["nombre"],
                    apellido=data["apellido"],
                    password=data["password"],
                    rol_id=data["rol_id"],
                    activo=data["activo"],
                ),
            )

    def _abrir_dialogo_editar_usuario(self, usuario: Usuario) -> None:
        dlg = UsuarioDialog(self, roles=self._roles, usuario=usuario)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.event_bus.emit(
                "guardar_usuario_requested",
                GuardarUsuarioRequestedEvent(
                    usuario_id=usuario.id,
                    username=data["username"],
                    nombre=data["nombre"],
                    apellido=data["apellido"],
                    password=data["password"],
                    rol_id=data["rol_id"],
                    activo=data["activo"],
                ),
            )

    def _confirmar_eliminar_usuario(self, usuario: Usuario) -> None:
        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar al usuario <b>{usuario.username}</b>?<br>Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.event_bus.emit(
                "eliminar_usuario_requested",
                EliminarUsuarioRequestedEvent(usuario_id=usuario.id),
            )

    # ── Diálogos Roles ────────────────────────────────────────────────────────

    def _abrir_dialogo_nuevo_rol(self) -> None:
        dlg = RolDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.event_bus.emit(
                "guardar_rol_requested",
                GuardarRolRequestedEvent(
                    rol_id=None,
                    nombre=data["nombre"],
                    descripcion=data["descripcion"],
                ),
            )

    def _abrir_dialogo_editar_rol(self, rol: Rol) -> None:
        dlg = RolDialog(self, rol=rol)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.event_bus.emit(
                "guardar_rol_requested",
                GuardarRolRequestedEvent(
                    rol_id=rol.id,
                    nombre=data["nombre"],
                    descripcion=data["descripcion"],
                ),
            )

    def _confirmar_eliminar_rol(self, rol: Rol) -> None:
        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar el rol <b>{rol.nombre}</b>?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.event_bus.emit(
                "eliminar_rol_requested",
                EliminarRolRequestedEvent(rol_id=rol.id),
            )

    # ── Estilos Dracula ───────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: #282a36;
                color: #f8f8f2;
            }

            /* Botón Nuevo */
            QPushButton#btnNuevo {
                background-color: #ff79c6;
                color: #282a36;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
            }
            QPushButton#btnNuevo:hover {
                background-color: #ff92d0;
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
                border: 1px solid #ff79c6;
            }

            /* Tabs */
            QTabWidget#usuariosTabs::pane {
                background-color: #282a36;
                border: 1px solid #44475a;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #1e1e2e;
                color: #6272a4;
                padding: 8px 18px;
                border: none;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #44475a;
                color: #f8f8f2;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #44475a;
            }

            /* Tablas */
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
                color: #ff79c6;
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
