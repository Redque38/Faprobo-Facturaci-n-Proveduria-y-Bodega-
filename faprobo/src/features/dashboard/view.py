from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QStackedWidget, QPushButton, QLabel, QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QIcon, QFont

from events.dashboard_events import NavigateToSectionEvent
from features.proveedores.view import ProveedoresView
from features.productos.view import ProductosView

class DashboardView(QMainWindow):
    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self.is_collapsed = False
        self.sidebar_width_expanded = 240
        self.sidebar_width_collapsed = 70

        self.setWindowTitle("Faprobo - Dashboard")
        self.resize(1280, 720)
        self.setMinimumSize(900, 600)

        # Aplicar tema Dracula global
        self.apply_dracula_theme()

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==================== SIDEBAR ====================
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(self.sidebar_width_expanded)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 15, 10, 15)
        sidebar_layout.setSpacing(8)

        # Toggle Button (arriba)
        self.btn_toggle = QPushButton("☰")
        self.btn_toggle.setFixedSize(50, 50)
        self.btn_toggle.setObjectName("toggleButton")
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        sidebar_layout.addWidget(self.btn_toggle, alignment=Qt.AlignmentFlag.AlignLeft)

        # Logo / Título
        self.logo_label = QLabel("FAPROBO")
        self.logo_label.setObjectName("logo")
        self.logo_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        sidebar_layout.addWidget(self.logo_label)

        # Espaciador
        sidebar_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Botones de navegación
        self.btn_overview = self._create_nav_button("Overview", "overview", "🏠")
        self.btn_ventas = self._create_nav_button("Ventas", "ventas", "📊")
        self.btn_productos = self._create_nav_button("Productos", "productos", "📦")
        self.btn_proveedores = self._create_nav_button("Proveedores", "proveedores", "👥")

        sidebar_layout.addWidget(self.btn_overview)
        sidebar_layout.addWidget(self.btn_ventas)
        sidebar_layout.addWidget(self.btn_productos)
        sidebar_layout.addWidget(self.btn_proveedores)

        sidebar_layout.addStretch()

        # ==================== CONTENIDO CENTRAL ====================
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()

        # Páginas
        self.page_overview = QLabel("📊 Overview\n\nBienvenido al Dashboard de Faprobo")
        self.page_ventas = QLabel("💰 Sección de Ventas")

        for page in [self.page_overview, self.page_ventas]:
            page.setAlignment(Qt.AlignmentFlag.AlignCenter)
            page.setStyleSheet("font-size: 24px; color: #f8f8f2;")

        # Módulo real de Productos
        self.page_productos = ProductosView(event_bus)

        # Módulo real de Proveedores
        self.page_proveedores = ProveedoresView(event_bus)

        self.stacked_widget.addWidget(self.page_overview)
        self.stacked_widget.addWidget(self.page_ventas)
        self.stacked_widget.addWidget(self.page_productos)
        self.stacked_widget.addWidget(self.page_proveedores)

        content_layout.addWidget(self.stacked_widget)

        # Agregar todo al layout principal
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_widget, stretch=1)

        # Suscripción al evento
        self.event_bus.subscribe("navigate_to_section", self.handle_navigation)

        # Estado inicial
        self._set_active_button(self.btn_overview)
        self.stacked_widget.setCurrentIndex(0)

    def apply_dracula_theme(self):
        """QSS completo estilo Dracula"""
        dracula_qss = """
        QMainWindow, QWidget {
            background-color: #282a36;
            color: #f8f8f2;
        }

        /* Sidebar */
        #sidebar {
            background-color: #1e1e2e;
            border-right: 1px solid #44475a;
        }

        /* Logo */
        #logo {
            color: #bd93f9;
            padding: 10px 15px;
        }

        /* Toggle Button */
        #toggleButton {
            background-color: transparent;
            border: none;
            font-size: 24px;
            color: #f8f8f2;
        }
        #toggleButton:hover {
            background-color: #44475a;
            border-radius: 8px;
        }

        /* Botones de navegación */
        QPushButton#navButton {
            text-align: left;
            padding: 12px 20px;
            background-color: transparent;
            color: #f8f8f2;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            min-height: 48px;
        }
        QPushButton#navButton:hover {
            background-color: #44475a;
        }
        QPushButton#navButton:checked, QPushButton#navButton[active="true"] {
            background-color: #44475a;
            color: #bd93f9;
            font-weight: bold;
        }

        /* Contenido */
        QStackedWidget {
            background-color: #282a36;
        }

        QLabel {
            color: #f8f8f2;
        }
        """
        self.setStyleSheet(dracula_qss)

    def _create_nav_button(self, text: str, section: str, icon: str) -> QPushButton:
        btn = QPushButton(f"  {icon}   {text}")
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.event_bus.emit("navigate_to_section", NavigateToSectionEvent(section)))
        return btn

    def _set_active_button(self, active_btn: QPushButton):
        for btn in [self.btn_overview, self.btn_ventas, self.btn_productos, self.btn_proveedores]:
            btn.setProperty("active", btn == active_btn)
            btn.setChecked(btn == active_btn)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def toggle_sidebar(self):
        """Animación para colapsar / expandir el sidebar"""
        start_width = self.sidebar.width()
        end_width = self.sidebar_width_collapsed if not self.is_collapsed else self.sidebar_width_expanded

        self.animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(start_width)
        self.animation.setEndValue(end_width)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.animation.start()

        self.is_collapsed = not self.is_collapsed

        # Ocultar/Mostrar texto del logo
        if self.is_collapsed:
            self.logo_label.hide()
            self.btn_toggle.setText("▶")
        else:
            self.logo_label.show()
            self.btn_toggle.setText("☰")

    def handle_navigation(self, event: NavigateToSectionEvent):
        sections = {
            "overview": 0,
            "ventas": 1,
            "productos": 2,
            "proveedores": 3
        }
        if event.section in sections:
            index = sections[event.section]
            self.stacked_widget.setCurrentIndex(index)
            self._set_active_button([
                self.btn_overview, self.btn_ventas,
                self.btn_productos, self.btn_proveedores
            ][index])

            # Cargar datos al entrar a la sección de proveedores
            if event.section == "proveedores":
                self.page_proveedores.cargar()
            elif event.section == "productos":
                self.page_productos.cargar()