# 🚀 Faprobo — Facturación, Proveeduría y Bodega

Sistema premium de gestión interna desarrollado en **Python** con **PySide6**, implementando una arquitectura robusta basada en el patrón **MVP (Model-View-Presenter)** y comunicación desacoplada mediante un **Event Bus**.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6-green?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![Architecture](https://img.shields.io/badge/Architecture-MVP-orange)](#arquitectura)
[![Linter](https://img.shields.io/badge/Linter-Ruff-red)](https://github.com/astral-sh/ruff)

---

## 🛠️ Estructura del Proyecto

```text
.
├── src/
│   ├── core/           # Clases base, EventBus y lógica central del sistema.
│   ├── events/         # Definición de señales y eventos (Login, UI, etc.).
│   ├── features/       # Módulos funcionales (Login, Dashboard, Productos, Proveedores).
│   │   └── <feature>/  # Cada módulo sigue el patrón Model - View - Presenter.
│   ├── services/       # Integraciones externas, API y base de datos.
│   ├── ui/             # Componentes visuales y widgets personalizados.
│   └── main.py         # Punto de entrada principal de la aplicación.
├── tests/              # Suite de pruebas unitarias y de integración.
├── pyproject.toml      # Configuración de Poetry y tareas de PoeThePoet.
└── README.md           # Documentación principal.
```

---

## 🚀 Instalación y Configuración

Este proyecto utiliza **Poetry** para la gestión de dependencias y entornos virtuales.

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/Redque38/Faprobo-Facturaci-n-Proveduria-y-Bodega-.git
    ```

2.  **Instalar dependencias:**
    ```bash
    # Si no tienes poe instalado globalmente, puedes usar poetry run poe
    poetry install
    ```

---

## ⚡ Comandos Rápidos (Automation)

Utilizamos `poethepoet` para simplificar las tareas comunes de desarrollo:

| Tarea | Comando | Descripción |
| :--- | :--- | :--- |
| **Ejecutar** | `poe run` | Inicia la aplicación principal. |
| **Formatear** | `poe format` | Aplica ruff format a todo el código. |
| **Linter** | `poe lint` | Ejecuta ruff para análisis estático. |
| **Tests** | `poe test` | Ejecuta la suite de pruebas con pytest. |
| **Limpieza** | `poe clean` | Elimina cachés y archivos temporales. |

---

## 🏗️ Arquitectura

La aplicación está diseñada para ser escalable y mantenible:

-   **Model**: Gestiona los datos y la lógica de negocio. Se comunica con los servicios.
-   **View**: Define la interfaz de usuario (PySide6) de manera pasiva.
-   **Presenter**: El intermediario que reacciona a los eventos de la vista y actualiza el modelo (o viceversa).
-   **Event Bus**: Sistema de mensajería centralizado que permite que diferentes módulos se comuniquen sin estar acoplados directamente.

---

## 🎨 Estética y Diseño
Diseñado con un enfoque en la experiencia de usuario moderna, utilizando paletas de colores armónicas y micro-animaciones para ofrecer una interfaz fluida y profesional.

---
© 2026 Developed by **Enrik**
