"""
Verificación manual de conectividad a MotherDuck.

Corré esto una sola vez para confirmar que:
  1. El .env se carga bien.
  2. El token es válido.
  3. La BD `faprobo_facturas` existe y tiene las tablas esperadas.

Uso (desde la raíz del proyecto):
    poetry run python scripts/verify_motherduck.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Asegura que src/ está en el path cuando se corre sin poe tasks
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core import config
from core.db.duckdb_client import DuckDBClient, DuckDBConfigError

TABLAS_ESPERADAS = {
    "facturas",
    "factura_lineas",
    "factura_cuotas",
    "factura_pagos",
    "productos",
    "proveedores",
}


def main() -> int:
    config.load()

    if not config.motherduck_token():
        print("[FAIL] MOTHERDUCK_TOKEN no está en el entorno (.env).")
        return 1
    print(f"[ OK ] Token presente ({len(config.motherduck_token())} chars)")
    print(f"[INFO] Base de datos: {config.motherduck_database()}")
    print(f"[INFO] Sucursal ID: {config.sucursal_id()}")

    try:
        client = DuckDBClient.from_config()
    except DuckDBConfigError as exc:
        print(f"[FAIL] No se pudo armar cliente: {exc}")
        return 1

    if not client.ping():
        print("[FAIL] Ping a MotherDuck falló (ver logs).")
        return 1
    print("[ OK ] Ping SELECT 1")

    # Listar tablas
    rows = client.fetchall(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='main' ORDER BY table_name"
    )
    encontradas = {r["table_name"] for r in rows}
    faltantes = TABLAS_ESPERADAS - encontradas
    extras = encontradas - TABLAS_ESPERADAS

    print(f"[INFO] Tablas en la BD: {sorted(encontradas) or '(ninguna)'}")
    if faltantes:
        print(f"[WARN] Faltan tablas esperadas: {sorted(faltantes)}")
    if extras:
        print(f"[INFO] Tablas adicionales: {sorted(extras)}")

    # Conteo rápido por tabla (diagnóstico)
    for t in sorted(encontradas & TABLAS_ESPERADAS):
        row = client.fetchone(f"SELECT COUNT(*) AS n FROM {t}")
        print(f"[INFO] {t:<20} filas: {row['n']}")

    if faltantes:
        print("\nACCION: aplicá `src/core/db/duckdb_schema.sql` en MotherDuck.")
        return 1

    print("\n[ OK ] Fase 3 conectividad verificada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
