# Faprobo — Facturación, Proveeduría y Bodega

Sistema de gestión interna desarrollado en Python con PyQt, siguiendo la arquitectura **MVP (Model-View-Presenter)**.

## Estructura del proyecto

```
faprobo/
├── resources/          # Iconos, imágenes y estilos QSS
├── src/
│   ├── core/           # EventBus y clases base reutilizables
│   ├── events/         # Definición de eventos por feature
│   ├── features/       # Módulos de la aplicación (login, dashboard, productos, ...)
│   ├── services/       # Servicios de datos (API, DB, simulados)
│   ├── ui/             # Widgets reutilizables
│   └── main.py         # Punto de entrada
├── .gitignore
├── README.md
└── requirements.txt
```

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python src/main.py
```
