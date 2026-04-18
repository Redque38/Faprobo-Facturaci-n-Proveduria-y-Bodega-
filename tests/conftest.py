"""
Configuración global de pytest.

- Agrega `src/` al sys.path para que los tests hagan `from core...` / `from features...`
  igual que el runtime (env PYTHONPATH=src en poe tasks).
- Fixture `tmp_sqlite` devuelve un SqliteManager apuntando a un archivo temporal
  con migraciones aplicadas, sin tocar `data/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Imports tardíos para asegurar que sys.path ya incluye src/
from core.db.sqlite_manager import SqliteManager  # noqa: E402
from core.db.migrations_runner import run_migrations  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_sqlite_cache():
    """Evita que instancias cacheadas crucen tests."""
    SqliteManager.reset_cache()
    yield
    SqliteManager.reset_cache()


@pytest.fixture
def facturas_db(tmp_path) -> SqliteManager:
    db_path = tmp_path / "facturas.db"
    run_migrations("facturas", db_path=db_path)
    return SqliteManager.get(db_path)


@pytest.fixture
def catalogo_db(tmp_path) -> SqliteManager:
    db_path = tmp_path / "catalogo.db"
    run_migrations("catalogo", db_path=db_path)
    return SqliteManager.get(db_path)
