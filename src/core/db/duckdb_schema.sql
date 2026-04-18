-- duckdb_schema.sql
-- Eschema DDL para DuckDB (orientado a análisis y centralización en MotherDuck)
-- Generado a partir del esquema local SQLite con adaptaciones para OLAP.

-- -----------------------------------------------------------------------------
-- Módulo: Facturación
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS facturas (
    id                  INTEGER,
    sucursal_id         INTEGER NOT NULL,
    tipo                VARCHAR NOT NULL,
    entidad_id          INTEGER NOT NULL,
    subtotal            DOUBLE NOT NULL DEFAULT 0,
    descuento           DOUBLE NOT NULL DEFAULT 0,
    impuesto            DOUBLE NOT NULL DEFAULT 0,
    total               DOUBLE NOT NULL DEFAULT 0,
    estado              VARCHAR NOT NULL DEFAULT 'pendiente',
    es_electronica      BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_creacion      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP,
    PRIMARY KEY (id, sucursal_id)
);

CREATE TABLE IF NOT EXISTS factura_lineas (
    id              INTEGER,
    sucursal_id     INTEGER NOT NULL,
    factura_id      INTEGER NOT NULL,
    producto_id     INTEGER NOT NULL,
    descripcion     VARCHAR NOT NULL,
    cantidad        DOUBLE NOT NULL,
    precio_unitario DOUBLE NOT NULL,
    descuento_linea DOUBLE NOT NULL DEFAULT 0,
    total_linea     DOUBLE NOT NULL,
    PRIMARY KEY (id, sucursal_id)
);

CREATE TABLE IF NOT EXISTS factura_cuotas (
    id                INTEGER,
    sucursal_id       INTEGER NOT NULL,
    factura_id        INTEGER NOT NULL,
    numero_cuota      INTEGER NOT NULL,
    monto             DOUBLE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    pagada            BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_pago        TIMESTAMP,
    PRIMARY KEY (id, sucursal_id)
);

CREATE TABLE IF NOT EXISTS factura_pagos (
    id         INTEGER,
    sucursal_id INTEGER NOT NULL,
    factura_id INTEGER NOT NULL,
    monto      DOUBLE NOT NULL,
    fecha_pago TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metodo     VARCHAR NOT NULL DEFAULT 'efectivo',
    PRIMARY KEY (id, sucursal_id)
);

-- -----------------------------------------------------------------------------
-- Módulo: Catálogo (Productos y Proveedores)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS productos (
    id             INTEGER,
    sucursal_id    INTEGER NOT NULL,
    codigo         VARCHAR NOT NULL,
    nombre         VARCHAR NOT NULL,
    descripcion    VARCHAR DEFAULT '',
    precio_compra  DOUBLE NOT NULL DEFAULT 0,
    precio_venta   DOUBLE NOT NULL DEFAULT 0,
    stock          INTEGER NOT NULL DEFAULT 0,
    categoria      VARCHAR DEFAULT '',
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP,
    PRIMARY KEY (id, sucursal_id)
);

CREATE TABLE IF NOT EXISTS proveedores (
    id             INTEGER,
    sucursal_id    INTEGER NOT NULL,
    nombre         VARCHAR NOT NULL,
    contacto       VARCHAR DEFAULT '',
    telefono       VARCHAR DEFAULT '',
    email          VARCHAR DEFAULT '',
    direccion      VARCHAR DEFAULT '',
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP,
    PRIMARY KEY (id, sucursal_id)
);

-- -----------------------------------------------------------------------------
-- Índices para mejorar el desempeño de reportes
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas(fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_facturas_entidad ON facturas(entidad_id);
CREATE INDEX IF NOT EXISTS idx_productos_codigo ON productos(codigo);
CREATE INDEX IF NOT EXISTS idx_lineas_producto ON factura_lineas(producto_id);
CREATE INDEX IF NOT EXISTS idx_lineas_factura ON factura_lineas(factura_id, sucursal_id);
