"""
DuckDBClient — wrapper delgado sobre la librería `duckdb` para MotherDuck.

Uso típico:
    client = DuckDBClient.from_config()
    client.execute("INSERT INTO facturas (...) VALUES (...)")
    rows = client.fetchall("SELECT * FROM facturas WHERE fecha >= ?", (d,))

Decisiones:
- Conexión vía `duckdb.connect("md:<db>?motherduck_token=<token>")`.
- `read_only=False` (necesitamos INSERT/UPDATE).
- Singleton por connection-string: reutiliza la conexión mientras viva el
  proceso. `reset_cache()` para tests.
- Los métodos aceptan parámetros posicionales (DuckDB también soporta `?`).
- `transaction()` es un contextmanager (BEGIN / COMMIT / ROLLBACK).
- `close()` desconecta y saca del cache.

Todos los métodos toman el lock para no pisarse si otro hilo está
ejecutando. DuckDB permite conexiones concurrentes, pero compartir una
misma conexión desde varios hilos requiere serialización.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Iterable, Optional, Sequence

from core import config

log = logging.getLogger(__name__)

try:
    import duckdb  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    duckdb = None  # type: ignore[assignment]


class DuckDBConfigError(RuntimeError):
    """Falta algún dato obligatorio (token, nombre de BD, etc.)."""


class DuckDBClient:
    """Wrapper con lock, cache por CS y helpers de alto nivel."""

    _instances: dict[str, "DuckDBClient"] = {}
    _class_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def __init__(self, connection_string: str) -> None:
        if duckdb is None:
            raise DuckDBConfigError(
                "La librería `duckdb` no está instalada. "
                "Agregala con `poetry add duckdb`."
            )
        self._cs = connection_string
        self._lock = threading.RLock()
        self._conn = duckdb.connect(connection_string, read_only=False)

    @classmethod
    def from_config(cls) -> "DuckDBClient":
        """
        Arma la connection-string desde variables de entorno:
        MOTHERDUCK_TOKEN + MOTHERDUCK_DATABASE.
        """
        token = config.motherduck_token()
        if not token:
            raise DuckDBConfigError(
                "Falta MOTHERDUCK_TOKEN en el entorno (.env). "
                "Ver Fase 3 del plan."
            )
        db = config.motherduck_database()
        cs = f"md:{db}?motherduck_token={token}"
        return cls.get(cs)

    @classmethod
    def get(cls, connection_string: str) -> "DuckDBClient":
        """Devuelve la instancia cacheada o crea una nueva."""
        with cls._class_lock:
            inst = cls._instances.get(connection_string)
            if inst is None:
                inst = cls(connection_string)
                cls._instances[connection_string] = inst
            return inst

    @classmethod
    def reset_cache(cls) -> None:
        """Cierra y descarta instancias cacheadas (tests / logout)."""
        with cls._class_lock:
            for inst in list(cls._instances.values()):
                try:
                    inst._conn.close()
                except Exception:  # noqa: BLE001
                    pass
            cls._instances.clear()

    # ------------------------------------------------------------------
    # Operaciones básicas
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        with self._lock:
            return self._conn.execute(sql, list(params) if params else None)

    def executemany(self, sql: str, seq_params: Iterable[Sequence[Any]]) -> Any:
        with self._lock:
            return self._conn.executemany(sql, [list(p) for p in seq_params])

    def executescript(self, script: str) -> None:
        """Ejecuta múltiples sentencias separadas por `;`."""
        with self._lock:
            self._conn.execute(script)

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[dict]:
        """
        Devuelve filas como lista de dicts (nombres de columna como llaves).
        """
        with self._lock:
            cur = self._conn.execute(sql, list(params) if params else None)
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> Optional[dict]:
        rows = self.fetchall(sql, params)
        return rows[0] if rows else None

    @contextmanager
    def transaction(self):
        """BEGIN / COMMIT / ROLLBACK."""
        with self._lock:
            self._conn.execute("BEGIN TRANSACTION")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            finally:
                with self.__class__._class_lock:
                    self.__class__._instances.pop(self._cs, None)

    def ping(self) -> bool:
        """Consulta trivial para validar conectividad. True si responde."""
        try:
            self.execute("SELECT 1")
            return True
        except Exception:  # noqa: BLE001
            log.exception("DuckDB ping falló")
            return False
