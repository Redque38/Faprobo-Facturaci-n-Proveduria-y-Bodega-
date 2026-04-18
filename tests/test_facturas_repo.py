"""Tests del FacturaRepository sobre una DB temporal."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from features.facturacion.repository import FacturaRepository


@pytest.fixture
def repo(facturas_db):
    return FacturaRepository(facturas_db)


def _linea(producto_id=1, cantidad=2.0, precio=100.0, descuento=0.0, descripcion="Item"):
    return {
        "producto_id": producto_id,
        "descripcion": descripcion,
        "cantidad": cantidad,
        "precio_unitario": precio,
        "descuento_linea": descuento,
    }


def test_crear_factura_con_lineas_y_cuotas(repo):
    fid = repo.crear_factura(
        tipo="venta",
        entidad_id=10,
        subtotal=200.0,
        descuento_global=0.0,
        impuesto=26.0,
        total=226.0,
        lineas=[_linea(), _linea(producto_id=2, cantidad=1, precio=50)],
        cuotas=[
            {"monto": 113.0, "fecha_vencimiento": "2026-05-01"},
            {"monto": 113.0, "fecha_vencimiento": "2026-05-15"},
        ],
    )
    f = repo.obtener_factura(fid)
    assert f is not None
    assert f["total"] == 226.0
    assert f["sync_duckdb"] == 0
    assert len(f["lineas"]) == 2
    assert len(f["cuotas"]) == 2
    assert f["cuotas"][0]["numero_cuota"] == 1


def test_anular_factura_cambia_estado(repo):
    fid = repo.crear_factura(
        tipo="venta", entidad_id=1, subtotal=100, descuento_global=0,
        impuesto=13, total=113, lineas=[_linea(precio=50)],
    )
    repo.anular_factura(fid)
    f = repo.obtener_factura(fid)
    assert f["estado"] == "anulada"


def test_registrar_pago_marca_pagada_al_cubrir_total(repo):
    fid = repo.crear_factura(
        tipo="venta", entidad_id=1, subtotal=100, descuento_global=0,
        impuesto=13, total=113, lineas=[_linea(precio=50)],
    )
    assert repo.registrar_pago(fid, 50.0) is False
    assert repo.obtener_factura(fid)["estado"] == "pendiente"

    assert repo.registrar_pago(fid, 63.0) is True
    assert repo.obtener_factura(fid)["estado"] == "pagada"


def test_listar_hoy_retorna_solo_facturas_de_hoy(repo, facturas_db):
    # Inserto una factura con fecha_creacion manual de ayer
    with facturas_db.transaction() as c:
        c.execute(
            "INSERT INTO facturas (tipo, entidad_id, subtotal, descuento, "
            "impuesto, total, fecha_creacion) "
            "VALUES (?,?,?,?,?,?, datetime('now','-1 day'))",
            ("venta", 1, 100, 0, 13, 113),
        )
    # Y otra de hoy
    repo.crear_factura(
        tipo="venta", entidad_id=2, subtotal=50, descuento_global=0,
        impuesto=6.5, total=56.5, lineas=[_linea(precio=25)],
    )

    hoy = repo.listar_hoy()
    assert len(hoy) == 1
    assert hoy[0]["entidad_id"] == 2


def test_pendientes_sync_y_marcar_sincronizadas(repo):
    ids = [
        repo.crear_factura(
            tipo="venta", entidad_id=i, subtotal=10, descuento_global=0,
            impuesto=1.3, total=11.3, lineas=[_linea(precio=5)],
        )
        for i in range(3)
    ]
    pendientes = repo.listar_pendientes_sync()
    assert {p["id"] for p in pendientes} == set(ids)

    repo.marcar_sincronizadas(ids[:2])
    restantes = repo.listar_pendientes_sync()
    assert [r["id"] for r in restantes] == [ids[2]]


def test_historia_temp_roundtrip(repo):
    registros = [
        {
            "id": 101, "tipo": "venta", "entidad_id": 1,
            "subtotal": 100, "descuento": 0, "impuesto": 13, "total": 113,
            "estado": "pagada", "es_electronica": 0,
            "fecha_creacion": "2026-03-01 10:00:00",
        },
        {
            "id": 102, "tipo": "venta", "entidad_id": 2,
            "subtotal": 200, "descuento": 0, "impuesto": 26, "total": 226,
            "estado": "pagada", "es_electronica": 0,
            "fecha_creacion": "2026-03-02 11:00:00",
        },
    ]
    n = repo.volcar_historia_temp(registros, periodo_key="2026-03")
    assert n == 2

    cacheados = repo.leer_historia_temp("2026-03")
    assert {r["id"] for r in cacheados} == {101, 102}

    # Re-volcar es idempotente (INSERT OR REPLACE)
    repo.volcar_historia_temp(registros, periodo_key="2026-03")
    assert len(repo.leer_historia_temp("2026-03")) == 2

    # Limpieza por período
    borrados = repo.limpiar_historia_temp("2026-03")
    assert borrados == 2
    assert repo.leer_historia_temp("2026-03") == []


def test_agregar_linea_recalcula_total(repo):
    fid = repo.crear_factura(
        tipo="venta", entidad_id=1, subtotal=100, descuento_global=0,
        impuesto=13, total=113, lineas=[_linea(precio=50)],
    )
    repo.agregar_linea(fid, _linea(producto_id=5, cantidad=1, precio=40))
    f = repo.obtener_factura(fid)
    # subtotal ahora suma las dos líneas (100 + 40), total = subtotal + impuesto original
    assert f["subtotal"] == 140.0
    assert f["total"] == round(140.0 + 13.0, 2)


def test_listar_por_rango(repo, facturas_db):
    # Crear manualmente con fechas controladas
    base = datetime(2026, 4, 10, 12, 0, 0)
    with facturas_db.transaction() as c:
        for i, delta in enumerate([-2, 0, 2], start=1):
            fecha = (base + timedelta(days=delta)).isoformat(sep=" ")
            c.execute(
                "INSERT INTO facturas (tipo, entidad_id, subtotal, descuento, "
                "impuesto, total, fecha_creacion) VALUES (?,?,?,?,?,?,?)",
                ("venta", i, 100, 0, 13, 113, fecha),
            )

    rango = repo.listar_por_rango(
        desde=base - timedelta(days=1),
        hasta=base + timedelta(days=1),
    )
    assert len(rango) == 1
