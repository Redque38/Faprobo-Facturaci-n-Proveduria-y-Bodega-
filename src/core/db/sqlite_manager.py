"""
SqliteManager: gestor de conexiones SQLite reutilizable.

Decisiones:
- Una conexión por archivo, compartida entre hilos (check_same_thread=False)
  y serializada con un Lock interno. Esto evita el costo de abrir/cerrar
  conexiones por operación sin sacrificar seguridad.
- Row factory = sqlite3.Row (acceso por nombre de columna).
- PRAGMAs aplicados al abrir: foreign_keys=ON, journal_mode=WAL,
  synchronous=NORMAL (buen balance durabilidad/rendimiento en WAL).
- Soporta ":memory:" para tests.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Union


PathLike = Union[str, Path]


class SqliteManager:
    """Maneja una conexión SQLite singleton por ruta de archivo."""

    _instances: dict[str, "SqliteManager"] = {}
    _instances_lock = threading.Lock()

    def __init__(self, db_path: PathLike):
        self._db_path_str = str(db_path)
        self._is_memory = self._db_path_str == ":memory:"
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        if not self._is_memory:
            Path(self._db_path_str).parent.mkdir(parents=True, exist_ok=True)
        self._open()

    # ------------------------------------------------------------------
    # Fábrica con caché por ruta (opcional — facilita reuso)
    # ------------------------------------------------------------------
    @classmethod
    def get(cls, db_path: PathLike) -> "SqliteManager":
        key = str(db_path)
        with cls._instances_lock:
            inst = cls._instances.get(key)
            if inst is None or inst._conn is None:
                inst = cls(db_path)
                cls._instances[key] = inst
            return inst

    @classmethod
    def reset_cache(cls) -> None:
        """Cierra y descarta todas las instancias cacheadas. Útil en tests."""
        with cls._instances_lock:
            for inst in cls._instances.values():
                inst.close()
            cls._instances.clear()

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------
    def _open(self) -> None:
        self._conn = sqlite3.connect(
            self._db_path_str,
            check_same_thread=False,
            isolation_level=None,  # autocommit; controlamos tx con BEGIN/COMMIT
            timeout=10.0,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        # WAL solo aplica a archivos en disco
        if not self._is_memory:
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._open()
        assert self._conn is not None
        return self._conn

    @property
    def db_path(self) -> str:
        return self._db_path_str

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None

    # ------------------------------------------------------------------
    # API transaccional
    # ------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Bloque transaccional thread-safe.
        Uso:
            with mgr.transaction() as c:
                c.execute(...)
        """
        with self._lock:
            conn = self.conn
            conn.execute("BEGIN")
            try:
                yield conn
            except Exception:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Ejecuta una sentencia sin transacción explícita (autocommit)."""
        with self._lock:
            return self.conn.execute(sql, params)

    def executescript(self, script: str) -> None:
        """Ejecuta un script SQL multi-sentencia."""
        with self._lock:
            self.conn.executescript(script)

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, params).fetchall()
