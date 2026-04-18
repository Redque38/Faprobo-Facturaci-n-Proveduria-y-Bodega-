-- 001_init.sql — Esquema base del módulo de Facturación
-- Debe ser idempotente: todas las tablas con IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS facturas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo                TEXT    NOT NULL CHECK(tipo IN ('venta','compra')),
    entidad_id          INTEGER NOT NULL,
    subtotal            REAL    NOT NULL DEFAULT 0,
    descuento           REAL    NOT NULL DEFAULT 0,
    impuesto            REAL    NOT NULL DEFAULT 0,
    total               REAL    NOT NULL DEFAULT 0,
    estado              TEXT    NOT NULL DEFAULT 'pendiente'
                                CHECK(estado IN ('pendiente','pagada','anulada')),
    es_electronica      INTEGER NOT NULL DEFAULT 0,
    sync_duckdb         INTEGER NOT NULL DEFAULT 0,   -- 0=pendiente, 1=sincronizada
    sync_attempts       INTEGER NOT NULL DEFAULT 0,
    sync_last_error     TEXT,
    fecha_creacion      TEXT    NOT NULL DEFAULT (datetime('now')),
    fecha_actualizacion TEXT
);

CREATE TABLE IF NOT EXISTS factura_lineas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id      INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
    producto_id     INTEGER NOT NULL,
    descripcion     TEXT    NOT NULL,
    cantidad        REAL    NOT NULL,
    precio_unitario REAL    NOT NULL,
    descuento_linea REAL    NOT NULL DEFAULT 0,
    total_linea     REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS factura_cuotas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id        INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
    numero_cuota      INTEGER NOT NULL,
    monto             REAL    NOT NULL,
    fecha_vencimiento TEXT    NOT NULL,
    pagada            INTEGER NOT NULL DEFAULT 0,
    fecha_pago        TEXT
);

CREATE TABLE IF NOT EXISTS factura_pagos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL REFERENCES facturas(id),
    monto      REAL    NOT NULL,
    fecha_pago TEXT    NOT NULL DEFAULT (datetime('now')),
    metodo     TEXT    NOT NULL DEFAULT 'efectivo'
);

-- Índices clave para los casos de uso del plan:
--  - listar "hoy" y por fecha
--  - encontrar facturas pendientes de sync
--  - filtrar por estado/tipo
CREATE INDEX IF NOT EXISTS ix_facturas_fecha        ON facturas(fecha_creacion);
CREATE INDEX IF NOT EXISTS ix_facturas_sync_pend    ON facturas(sync_duckdb) WHERE sync_duckdb = 0;
CREATE INDEX IF NOT EXISTS ix_facturas_tipo_estado  ON facturas(tipo, estado);
CREATE INDEX IF NOT EXISTS ix_lineas_factura        ON factura_lineas(factura_id);
CREATE INDEX IF NOT EXISTS ix_cuotas_factura        ON factura_cuotas(factura_id);
CREATE INDEX IF NOT EXISTS ix_pagos_factura         ON factura_pagos(factura_id);
