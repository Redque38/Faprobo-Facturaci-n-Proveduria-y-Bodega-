"""Tests de ProductoRepository y ProveedorRepository."""
from __future__ import annotations

import pytest

from features.productos.repository import ProductoRepository
from features.proveedores.repository import ProveedorRepository


@pytest.fixture
def prod_repo(catalogo_db):
    return ProductoRepository(catalogo_db)


@pytest.fixture
def prov_repo(catalogo_db):
    return ProveedorRepository(catalogo_db)


# --------------------------- Productos ------------------------------

def test_crear_y_listar_productos(prod_repo):
    p = prod_repo.crear(
        codigo="X001", nombre="Caja", descripcion="Cartón",
        precio_compra=1.0, precio_venta=2.0, stock=10, categoria="Empaque",
    )
    assert p.id > 0
    assert prod_repo.obtener(p.id).codigo == "X001"
    listado = prod_repo.listar()
    assert any(x.codigo == "X001" for x in listado)


def test_codigo_unico_productos(prod_repo):
    prod_repo.crear(
        codigo="DUP", nombre="A", descripcion="",
        precio_compra=1, precio_venta=2, stock=1, categoria="",
    )
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        prod_repo.crear(
            codigo="DUP", nombre="B", descripcion="",
            precio_compra=1, precio_venta=2, stock=1, categoria="",
        )


def test_actualizar_producto(prod_repo):
    p = prod_repo.crear(
        codigo="U001", nombre="Antes", descripcion="",
        precio_compra=1, precio_venta=2, stock=5, categoria="Cat",
    )
    actualizado = prod_repo.actualizar(
        p.id,
        codigo="U001", nombre="Después", descripcion="Nueva",
        precio_compra=1.5, precio_venta=3.0, stock=8, categoria="Cat2",
    )
    assert actualizado is not None
    assert actualizado.nombre == "Después"
    assert actualizado.stock == 8


def test_eliminar_es_baja_logica(prod_repo):
    p = prod_repo.crear(
        codigo="E001", nombre="Tmp", descripcion="",
        precio_compra=1, precio_venta=2, stock=1, categoria="",
    )
    assert prod_repo.eliminar(p.id) is True
    # Obtener aún devuelve el registro (existe físicamente)
    assert prod_repo.obtener(p.id) is not None
    # Pero listar() por defecto excluye inactivos
    assert all(x.id != p.id for x in prod_repo.listar())
    # Con incluir_inactivos=True reaparece
    assert any(x.id == p.id for x in prod_repo.listar(incluir_inactivos=True))


def test_actualizar_stock(prod_repo):
    p = prod_repo.crear(
        codigo="S001", nombre="Stock", descripcion="",
        precio_compra=1, precio_venta=2, stock=10, categoria="",
    )
    assert prod_repo.actualizar_stock(p.id, -3) == 7
    assert prod_repo.actualizar_stock(p.id, 5) == 12
    assert prod_repo.actualizar_stock(9999, 1) is None


def test_seed_si_vacio_solo_una_vez(prod_repo):
    primera = prod_repo.seed_si_vacio()
    segunda = prod_repo.seed_si_vacio()
    assert primera > 0
    assert segunda == 0


# --------------------------- Proveedores ----------------------------

def test_crud_proveedores(prov_repo):
    p = prov_repo.crear(
        nombre="Prov1", contacto="Juan", telefono="1111",
        email="j@p.com", direccion="SJ",
    )
    assert prov_repo.obtener(p.id).nombre == "Prov1"

    actualizado = prov_repo.actualizar(
        p.id, nombre="Prov1 v2", contacto="Juan", telefono="1111",
        email="j@p.com", direccion="SJ",
    )
    assert actualizado.nombre == "Prov1 v2"

    assert prov_repo.eliminar(p.id) is True
    assert all(x.id != p.id for x in prov_repo.listar())
