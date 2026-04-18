from dataclasses import dataclass

@dataclass
class NavigateToSectionEvent:
    """Evento para cambiar de sección en el dashboard"""
    section: str   # "overview", "facturacion", "productos", "proveedores"