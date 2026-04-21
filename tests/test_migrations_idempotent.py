"""Tests de idempotencia del runner de migraciones."""
from __future__ import annotations

from core.db.migrations_runner import run_migrations
from core.db.sqlite_manager import SqliteManager


def test_facturas_migrations_apply_once(tmp_path):
    db = tmp_path / "facturas.db"
    applied = run_migrations("facturas", db_path=db)
    assert 1 in applied and 2 in applied

    mgr = SqliteManager.get(db)
    tables = {
        r["name"]
        for r in mgr.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"facturas", "factura_lineas", "factura_cuotas",
            "factura_pagos", "facturas_historia_temp", "schema_version"} <= tables

    # Columnas clave para sync
    cols = {r["name"] for r in mgr.fetchall("PRAGMA table_info(facturas)")}
    assert {"sync_duckdb", "sync_attempts", "sync_last_error"} <= cols


def test_run_migrations_is_idempotent(tmp_path):
    db = tmp_path / "facturas.db"

    first = run_migrations("facturas", db_path=db)
    assert first, "Primera corrida debería aplicar migraciones."

    # Segunda corrida: nada nuevo que aplicar
    second = run_migrations("facturas", db_path=db)
    assert second == [], "Segunda corrida no debe reaplicar migraciones."


def test_catalogo_migrations_apply(tmp_path):
    db = tmp_path / "catalogo.db"
    applied = run_migrations("catalogo", db_path=db)
    assert 1 in applied

    mgr = SqliteManager.get(db)
    tables = {
        r["name"]
        for r in mgr.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"productos", "proveedores", "schema_version"} <= tables
