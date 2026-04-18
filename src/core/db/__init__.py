"""
Capa de acceso a datos SQLite local.

Expone:
- SqliteManager: conexión singleton por archivo con PRAGMAs correctos.
- run_migrations: aplica migraciones .sql de forma idempotente.
- bootstrap_databases: conveniencia para arrancar todas las DBs del sistema.
"""
from core.db.sqlite_manager import SqliteManager
from core.db.migrations_runner import run_migrations, bootstrap_databases

__all__ = ["SqliteManager", "run_migrations", "bootstrap_databases"]
