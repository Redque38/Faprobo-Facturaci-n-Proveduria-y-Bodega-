"""
Tests de FacturacionModel.cargar_historial — Fase 5.

Se prueba contra la caché local (`facturas_historia_temp`) usando un
downloader stub en lugar de MotherDuck. Verifica:

- Sin downloader, sin caché ⇒ lista vacía (no falla).
- Con downloader, primera consulta ⇒ se invoca y se vuelca en caché.
- Segunda consulta ⇒ ya hay caché, el downloader NO se vuelve a llamar.
- `refrescar=True` ⇒ re-descarga aunque haya caché.
- Registros fuera del rango de consulta NO aparecen.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from core.event_bus import EventBus
from features.facturacion.model import FacturacionModel
from features.facturacion.repository import FacturaRepository


def _registro(**overrides) -> dict:
    base = {
        "id": 1,
        "tipo": "venta",
        "entidad_id": 10,
        "subtotal": 1000.0,
        "descuento": 0.0,
        "impuesto": 130.0,
        "total": 1130.0,
        "estado": "pagada",
        "es_electronica": 0,
        "fecha_creacion": "2026-04-10T12:00:00",
    }
    base.update(overrides)
    return base


@pytest.fixture
def model(facturas_db) -> FacturacionModel:
    repo = FacturaRepository(facturas_db)
    return FacturacionModel(event_bus=EventBus(), repository=repo)


def test_sin_downloader_sin_cache_retorna_vacio(model):
    res = model.cargar_historial(
        datetime(2026, 4, 1), datetime(2026, 4, 30)
    )
    assert res == []


def test_descarga_si_cache_vacia(model):
    llamadas: list[tuple[datetime, datetime]] = []

    def downloader(desde, hasta):
        llamadas.append((desde, hasta))
        return [_registro(id=1), _registro(id=2)]

    model.set_historial_downloader(downloader)
    res = model.cargar_historial(
        datetime(2026, 4, 1), datetime(2026, 4, 30)
    )

    assert len(llamadas) == 1
    assert len(res) == 2
    assert {r["id"] for r in res} == {1, 2}


def test_segunda_consulta_no_redescarga(model):
    llamadas: list = []

    def downloader(desde, hasta):
        llamadas.append(1)
        return [_registro(id=1)]

    model.set_historial_downloader(downloader)
    model.cargar_historial(datetime(2026, 4, 1), datetime(2026, 4, 30))
    # Segunda consulta al mismo rango: ya hay caché
    res = model.cargar_historial(datetime(2026, 4, 1), datetime(2026, 4, 30))

    assert len(llamadas) == 1
    assert len(res) == 1


def test_refrescar_true_redescarga(model):
    llamadas: list = []

    def downloader(desde, hasta):
        llamadas.append(1)
        return [_registro(id=1, total=1130.0 + len(llamadas))]

    model.set_historial_downloader(downloader)
    model.cargar_historial(datetime(2026, 4, 1), datetime(2026, 4, 30))
    model.cargar_historial(
        datetime(2026, 4, 1), datetime(2026, 4, 30), refrescar=True
    )

    assert len(llamadas) == 2


def test_rango_excluye_fuera(model):
    def downloader(desde, hasta):
        # Devolvemos tres: uno dentro, dos fuera (antes y después)
        return [
            _registro(id=1, fecha_creacion="2026-03-15T10:00:00"),
            _registro(id=2, fecha_creacion="2026-04-15T10:00:00"),
            _registro(id=3, fecha_creacion="2026-05-15T10:00:00"),
        ]

    model.set_historial_downloader(downloader)
    res = model.cargar_historial(
        datetime(2026, 4, 1), datetime(2026, 4, 30)
    )

    ids = {r["id"] for r in res}
    assert ids == {2}


def test_downloader_que_devuelve_none_no_rompe(model):
    """Si el downloader devuelve None (error silencioso), no revienta."""
    def downloader(desde, hasta):
        return None  # noqa: RET501

    model.set_historial_downloader(downloader)
    res = model.cargar_historial(
        datetime(2026, 4, 1), datetime(2026, 4, 30)
    )
    assert res == []


def test_formato_de_fecha_con_espacio_tambien_funciona(model):
    """
    MotherDuck podría devolver fechas en formato 'YYYY-MM-DD HH:MM:SS'
    (con espacio) en vez de 'T'. El repo usa datetime() en la query, así
    que debe normalizar al comparar.
    """
    def downloader(desde, hasta):
        return [_registro(id=1, fecha_creacion="2026-04-10 12:00:00")]

    model.set_historial_downloader(downloader)
    res = model.cargar_historial(
        datetime(2026, 4, 1), datetime(2026, 4, 30)
    )
    assert len(res) == 1 and res[0]["id"] == 1
