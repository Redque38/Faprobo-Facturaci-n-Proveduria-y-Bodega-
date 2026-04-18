-- 002_historia_temp.sql — Caché local de consultas históricas traídas de DuckDB.
-- Se poblará bajo demanda cuando el usuario consulte un período en "Historial".
-- Estructura paralela a facturas pero sin integridad referencial (es un snapshot).

CREATE TABLE IF NOT EXISTS facturas_historia_temp (
    id             INTEGER NOT NULL,             -- id original en DuckDB
    tipo           TEXT    NOT NULL,
    entidad_id     INTEGER NOT NULL,
    subtotal       REAL    NOT NULL,
    descuento      REAL    NOT NULL,
    impuesto       REAL    NOT NULL,
    total          REAL    NOT NULL,
    estado         TEXT    NOT NULL,
    es_electronica INTEGER NOT NULL DEFAULT 0,
    fecha_creacion TEXT    NOT NULL,
    -- Metadata de la caché
    cached_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    periodo_key    TEXT    NOT NULL,             -- ej: "2026-04" o "2026-04-01_2026-04-15"
    PRIMARY KEY (id, periodo_key)
);

CREATE INDEX IF NOT EXISTS ix_historia_fecha   ON facturas_historia_temp(fecha_creacion);
CREATE INDEX IF NOT EXISTS ix_historia_periodo ON facturas_historia_temp(periodo_key);
