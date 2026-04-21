"""
Configuración global — carga .env y expone los valores tipados.

Se llama `load()` una sola vez al arrancar la app; después cualquier módulo
lee con `get(...)` sin saber si el valor vino de .env o del entorno real.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


_LOADED = False


def load(env_path: Optional[str | Path] = None) -> None:
    """Lee `.env` (si existe). Idempotente — llamalo en main.py."""
    global _LOADED
    if _LOADED:
        return
    if load_dotenv is None:
        # python-dotenv no instalado → solo usamos env vars del SO
        _LOADED = True
        return

    if env_path is None:
        # Busca .env subiendo desde cwd hasta la raíz del proyecto
        cur = Path.cwd()
        for candidate in (cur, *cur.parents):
            f = candidate / ".env"
            if f.is_file():
                env_path = f
                break

    if env_path and Path(env_path).is_file():
        load_dotenv(dotenv_path=env_path, override=False)
    _LOADED = True


def get(key: str, default: Any = None) -> Any:
    """Devuelve el valor de una variable (env > default)."""
    return os.environ.get(key, default)


def get_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False
    return default


# ---------------------------------------------------------------------------
# Claves conocidas (para autocompletar y evitar typos)
# ---------------------------------------------------------------------------
MOTHERDUCK_TOKEN      = "MOTHERDUCK_TOKEN"
MOTHERDUCK_DATABASE   = "MOTHERDUCK_DATABASE"
FAPROBO_SUCURSAL_ID   = "FAPROBO_SUCURSAL_ID"
FAPROBO_TZ            = "FAPROBO_TZ"


def sucursal_id() -> int:
    return get_int(FAPROBO_SUCURSAL_ID, 1)


def motherduck_database() -> str:
    return get(MOTHERDUCK_DATABASE, "faprobo_facturas")


def motherduck_token() -> Optional[str]:
    return get(MOTHERDUCK_TOKEN)


def tz() -> str:
    return get(FAPROBO_TZ, "America/Costa_Rica")
