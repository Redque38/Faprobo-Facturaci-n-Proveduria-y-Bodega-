"""
Tests del SyncService — Fase 3.

El DuckDBClient se mockea con un doble que:
- Registra cada execute/executemany para verificar el SQL emitido.
- Tiene un contextmanager `transaction()` con BEGIN/COMMIT/ROLLBACK simulados.
- Permite configurar que `transaction()` lance excepción en el N-ésimo uso
  (para probar reintentos).

Los eventos del bus se capturan con un listener por clase.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pytest

from core.event_bus import EventBus
from events.facturacion_events import (
    CierreCajaSolicitado,
    SincronizacionCompletada,
    SincronizacionFallida,
    SincronizacionIniciada,
)
from features.facturacion.model import FacturacionModel
from features.facturacion.repository import FacturaRepository
from features.sync.sync_service import SyncService


# ---------------------------------------------------------------------------
# Doble del DuckDBClient
# ---------------------------------------------------------------------------
@dataclass
class _Call:
    sql: str
    params: Any


class FakeDuckDB:
    """Mock mínimo con la superficie de API que SyncService usa."""

    def __init__(self, fail_on_upsert_ids: set[int] | None = None):
        self.calls: list[_Call] = []
        self._fail_ids = fail_on_upsert_ids or set()
        self._current_factura_id: int | None = None
        self.fetch_response: list[dict] = []
        self.tx_depth = 0
        self.tx_rollbacks = 0

    def execute(self, sql, params=()):
        self.calls.append(_Call(sql, params))
        # Si estamos dentro de una transacción y esta factura debe fallar
        # al insertar la cabecera, lanzamos acá.
        if "INSERT OR REPLACE INTO facturas" in sql and params:
            fid = params[0]
            if fid in self._fail_ids:
                raise RuntimeError(f"fallo simulado en factura {fid}")
        class _C: pass
        return _C()

    def executemany(self, sql, seq):
        self.calls.append(_Call(sql, list(seq)))

    def fetchall(self, sql, params=()):
        self.calls.append(_Call(sql, params))
        return self.fetch_response

    @contextmanager
    def transaction(self):
        self.tx_depth += 1
        try:
            yield self
        except Exception:
            self.tx_rollbacks += 1
            raise
        finally:
            self.tx_depth -= 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def repo(facturas_db) -> FacturaRepository:
    return FacturaRepository(facturas_db)


@pytest.fixture
def model(bus, repo) -> FacturacionModel:
    return FacturacionModel(event_bus=bus, repository=repo)


def _capture(bus: EventBus):
    capturados: dict[type, list] = {
        SincronizacionIniciada: [],
        SincronizacionCompletada: [],
        SincronizacionFallida: [],
    }
    for k in capturados:
        bus.subscribe(k, capturados[k].append)
    return capturados


def _crear_factura(model, *, tipo="venta", entidad_id=1, monto=100.0) -> int:
    return model.crear_factura(
        tipo=tipo, entidad_id=entidad_id,
        lineas=[{"producto_id": 1, "descripcion": "X",
                 "cantidad": 1, "precio_unitario": monto}],
    )


# ---------------------------------------------------------------------------
# Tests — PUSH
# ---------------------------------------------------------------------------
def test_push_sin_pendientes_emite_completada_cero(bus, repo):
    svc = SyncService(bus, repository=repo, duckdb_client=FakeDuckDB(), sucursal_id=1)
    eventos = _capture(bus)

    enviados = svc.push_pendientes()

    assert enviados == 0
    assert len(eventos[SincronizacionIniciada]) == 1
    assert len(eventos[SincronizacionCompletada]) == 1
    assert eventos[SincronizacionCompletada][0].registros_enviados == 0


def test_push_dos_pendientes_emite_completada(bus, repo, model):
    fake = FakeDuckDB()
    svc = SyncService(bus, repository=repo, duckdb_client=fake, sucursal_id=7)
    _crear_factura(model)
    _crear_factura(model, tipo="compra", entidad_id=2, monto=50.0)
    eventos = _capture(bus)

    enviados = svc.push_pendientes()

    assert enviados == 2
    assert len(eventos[SincronizacionCompletada]) == 1
    # Cabecera: debe usar sucursal_id inyectado = 7
    cabeceras = [c for c in fake.calls if "INSERT OR REPLACE INTO facturas" in c.sql]
    assert len(cabeceras) == 2
    assert all(c.params[1] == 7 for c in cabeceras)
    # Después del push, ya no quedan pendientes.
    assert repo.listar_pendientes_sync() == []


def test_push_factura_que_falla_suma_intento_y_sigue(bus, repo, model):
    fid1 = _crear_factura(model)
    fid2 = _crear_factura(model, tipo="compra", entidad_id=2)

    fake = FakeDuckDB(fail_on_upsert_ids={fid1})
    svc = SyncService(bus, repository=repo, duckdb_client=fake, sucursal_id=1)
    eventos = _capture(bus)

    enviados = svc.push_pendientes()

    assert enviados == 1  # fid2 sí pasó
    # fid1 suma 1 intento, sigue pendiente pero con error registrado
    pend = {f["id"]: f for f in repo.listar_pendientes_sync()}
    assert fid1 in pend and pend[fid1]["sync_attempts"] == 1
    assert "fallo simulado" in (pend[fid1]["sync_last_error"] or "")
    # fid2 ya no está pendiente
    assert fid2 not in pend
    # Rollback ocurrió en la transacción fallida
    assert fake.tx_rollbacks == 1
    # Se publicó Fallida (no Completada) porque 1 de 2 falló
    assert len(eventos[SincronizacionFallida]) == 1
    assert len(eventos[SincronizacionCompletada]) == 0


def test_push_tres_fallos_consecutivos_bloquea(bus, repo, model):
    fid = _crear_factura(model)
    fake = FakeDuckDB(fail_on_upsert_ids={fid})
    svc = SyncService(bus, repository=repo, duckdb_client=fake, sucursal_id=1)

    svc.push_pendientes()  # intento 1
    svc.push_pendientes()  # intento 2
    svc.push_pendientes()  # intento 3

    pend = repo.listar_pendientes_sync()
    # Después de 3 intentos fallidos queda fuera del listado de pendientes
    assert pend == []

    # Pero sigue en la tabla con sync_attempts=3 (lo verificamos con un select directo)
    row = repo._mgr.fetchone("SELECT sync_attempts FROM facturas WHERE id=?", (fid,))
    assert row["sync_attempts"] == 3

    # reintentar_sync() la devuelve al pool
    repo.reintentar_sync(fid)
    pend2 = repo.listar_pendientes_sync()
    assert any(f["id"] == fid for f in pend2)


def test_factura_anulada_se_sincroniza(bus, repo, model):
    fid = _crear_factura(model)
    fake = FakeDuckDB()
    svc = SyncService(bus, repository=repo, duckdb_client=fake, sucursal_id=1)

    svc.push_pendientes()  # sincroniza la creada
    assert repo.listar_pendientes_sync() == []

    # Anular debe resetear sync_duckdb → vuelve a pendientes
    model.anular_factura(fid, motivo="Test")
    pend = repo.listar_pendientes_sync()
    assert len(pend) == 1 and pend[0]["estado"] == "anulada"

    svc.push_pendientes()
    assert repo.listar_pendientes_sync() == []

    # La cabecera se reenvió con estado 'anulada'
    cabeceras = [c for c in fake.calls if "INSERT OR REPLACE INTO facturas" in c.sql]
    estados = [c.params[8] for c in cabeceras]
    assert estados[-1] == "anulada"


def test_pago_reabre_sync(bus, repo, model):
    fid = _crear_factura(model, monto=100.0)
    fake = FakeDuckDB()
    svc = SyncService(bus, repository=repo, duckdb_client=fake, sucursal_id=1)
    svc.push_pendientes()
    assert repo.listar_pendientes_sync() == []

    # Registrar pago completo
    model.registrar_pago(fid, monto=113.0, metodo="efectivo")
    pend = repo.listar_pendientes_sync()
    assert any(f["id"] == fid for f in pend)


def test_cierre_caja_dispara_push(bus, repo, model):
    _crear_factura(model)
    fake = FakeDuckDB()
    SyncService(bus, repository=repo, duckdb_client=fake, sucursal_id=1)

    bus.publish(CierreCajaSolicitado())

    # Debe haber sincronizado la factura
    assert repo.listar_pendientes_sync() == []


# ---------------------------------------------------------------------------
# Tests — FETCH historial (downloader)
# ---------------------------------------------------------------------------
def test_fetch_historial_normaliza_tipos(bus, repo):
    from datetime import datetime

    fake = FakeDuckDB()
    fake.fetch_response = [{
        "id": 42, "tipo": "venta", "entidad_id": 5,
        "subtotal": 100, "descuento": 0, "impuesto": 13, "total": 113,
        "estado": "pagada", "es_electronica": True,
        "fecha_creacion": datetime(2026, 4, 10, 12, 0, 0),
    }]
    svc = SyncService(bus, repository=repo, duckdb_client=fake, sucursal_id=1)

    out = svc.fetch_historial(datetime(2026, 4, 1), datetime(2026, 4, 30))

    assert len(out) == 1
    r = out[0]
    # datetime → string (lo que espera volcar_historia_temp)
    assert isinstance(r["fecha_creacion"], str)
    # bool → int
    assert r["es_electronica"] == 1
    # Tipos numéricos → float
    assert isinstance(r["total"], float)


def test_como_downloader_enchufa_a_cargar_historial(bus, repo, model):
    from datetime import datetime

    fake = FakeDuckDB()
    fake.fetch_response = [{
        "id": 1, "tipo": "venta", "entidad_id": 1,
        "subtotal": 50, "descuento": 0, "impuesto": 6.5, "total": 56.5,
        "estado": "pagada", "es_electronica": False,
        "fecha_creacion": datetime(2026, 3, 15, 10, 0),
    }]
    svc = SyncService(bus, repository=repo, duckdb_client=fake, sucursal_id=1)
    model.set_historial_downloader(svc.como_downloader())

    out = model.cargar_historial(datetime(2026, 3, 1), datetime(2026, 3, 31))

    assert len(out) == 1 and out[0]["id"] == 1
    # Segunda consulta al mismo rango no vuelve a llamar al fetch (hay caché)
    fake.fetch_response = []  # si vuelve a llamar, rompería el assert
    out2 = model.cargar_historial(datetime(2026, 3, 1), datetime(2026, 3, 31))
    assert len(out2) == 1


# ---------------------------------------------------------------------------
# Test — config ausente
# ---------------------------------------------------------------------------
def test_sin_duckdb_client_ni_config_publica_fallida(bus, repo, monkeypatch):
    """Si no hay MOTHERDUCK_TOKEN y tampoco se inyectó cliente, falla limpio."""
    import os
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)

    svc = SyncService(bus, repository=repo, duckdb_client=None, sucursal_id=1)
    eventos = _capture(bus)

    enviados = svc.push_pendientes()

    assert enviados == 0
    assert len(eventos[SincronizacionFallida]) == 1
    assert "MOTHERDUCK_TOKEN" in eventos[SincronizacionFallida][0].error
