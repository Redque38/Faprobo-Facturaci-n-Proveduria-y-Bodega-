-- 001_init.sql — Bitácora de auditoría del sistema.
-- Registra toda acción significativa: quién, qué, cuándo.

CREATE TABLE IF NOT EXISTS bitacora (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    usuario_nom TEXT    NOT NULL DEFAULT 'sistema',
    modulo      TEXT    NOT NULL,          -- 'facturacion' | 'pos' | 'productos' | ...
    accion      TEXT    NOT NULL,          -- 'factura_creada' | 'login' | ...
    descripcion TEXT    NOT NULL DEFAULT ''
);

-- Índices para los filtros más comunes en la vista
CREATE INDEX IF NOT EXISTS ix_bitacora_timestamp ON bitacora(timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_bitacora_modulo    ON bitacora(modulo);
CREATE INDEX IF NOT EXISTS ix_bitacora_usuario   ON bitacora(usuario_nom);
