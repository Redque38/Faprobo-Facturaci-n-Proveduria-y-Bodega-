"""
Runner de migraciones idempotente.

Cada DB tiene su propia carpeta en src/core/db/migrations/<nombre_db>/
con archivos nombrados 001_xxx.sql, 002_yyy.sql, etc.

Se registran en la tabla `schema_version(version INT PRIMARY KEY, applied_at TEXT)`.
Una migración que ya está registrada no se vuelve a ejecutar.

Regla: el contenido de cada .sql DEBE ser idempotente aun si se ejecuta
dos veces (usar CREATE TABLE IF NOT EXISTS, ADD COLUMN con guardas, etc.).
La tabla schema_version es un seguro de más, no una excusa para no ser idempotente.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.db.sqlite_manager import SqliteManager


MIGRATIONS_ROOT = Path(__file__).parent / "migrations"

# Mapeo de DB lógica -> ruta física por defecto
DEFAULT_DB_PATHS = {
    "facturas": "data/facturas.db",
    "catalogo": "data/catalogo.db",
}


def _ensure_version_table(mgr: SqliteManager) -> None:
    mgr.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version    INTEGER PRIMARY KEY,
            filename   TEXT    NOT NULL,
            applied_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _applied_versions(mgr: SqliteManager) -> set[int]:
    rows = mgr.fetchall("SELECT version FROM schema_version")
    return {int(r["version"]) for r in rows}


def _discover_migrations(db_name: str) -> list[tuple[int, Path]]:
    folder = MIGRATIONS_ROOT / db_name
    if not folder.is_dir():
        return []
    found: list[tuple[int, Path]] = []
    for p in sorted(folder.glob("*.sql")):
        stem = p.stem  # ej: "001_init"
        num_str = stem.split("_", 1)[0]
        try:
            version = int(num_str)
        except ValueError:
            raise ValueError(
                f"Migración con nombre inválido (debe empezar con dígitos): {p.name}"
            )
        found.append((version, p))
    return found


def run_migrations(db_name: str, db_path: str | Path | None = None) -> list[int]:
    """
    Aplica todas las migraciones pendientes de `db_name`.

    Returns: lista de versiones aplicadas en esta corrida (vacía si todo al día).
    """
    resolved_path = str(db_path) if db_path is not None else DEFAULT_DB_PATHS.get(db_name)
    if resolved_path is None:
        raise KeyError(
            f"No hay ruta por defecto para DB '{db_name}'. "
            f"Pásala explícita o registrala en DEFAULT_DB_PATHS."
        )

    mgr = SqliteManager.get(resolved_path)
    _ensure_version_table(mgr)
    applied = _applied_versions(mgr)

    newly_applied: list[int] = []
    for version, path in _discover_migrations(db_name):
        if version in applied:
            continue
        script = path.read_text(encoding="utf-8")
        # Nota: sqlite3.Connection.executescript() emite un COMMIT implícito
        # antes de correr, así que no podemos envolverlo en una tx manual.
        # Los .sql se escriben idempotentes a propósito; si el INSERT de
        # schema_version fallara, la reejecución es segura.
        mgr.executescript(script)
        mgr.execute(
            "INSERT INTO schema_version (version, filename) VALUES (?, ?)",
            (version, path.name),
        )
        newly_applied.append(version)
    return newly_applied


def bootstrap_databases(db_names: Iterable[str] = ("facturas", "catalogo")) -> dict[str, list[int]]:
    """Corre las migraciones de varias DBs. Devuelve qué versiones aplicó en cada una."""
    result: dict[str, list[int]] = {}
    for name in db_names:
        result[name] = run_migrations(name)
    return result
