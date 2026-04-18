-- 001_init.sql — Catálogo de productos y proveedores.

CREATE TABLE IF NOT EXISTS productos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo         TEXT    NOT NULL UNIQUE,
    nombre         TEXT    NOT NULL,
    descripcion    TEXT    NOT NULL DEFAULT '',
    precio_compra  REAL    NOT NULL DEFAULT 0,
    precio_venta   REAL    NOT NULL DEFAULT 0,
    stock          INTEGER NOT NULL DEFAULT 0,
    categoria      TEXT    NOT NULL DEFAULT '',
    activo         INTEGER NOT NULL DEFAULT 1,
    fecha_creacion TEXT    NOT NULL DEFAULT (datetime('now')),
    fecha_actualizacion TEXT
);

CREATE TABLE IF NOT EXISTS proveedores (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT    NOT NULL,
    contacto       TEXT    NOT NULL DEFAULT '',
    telefono       TEXT    NOT NULL DEFAULT '',
    email          TEXT    NOT NULL DEFAULT '',
    direccion      TEXT    NOT NULL DEFAULT '',
    activo         INTEGER NOT NULL DEFAULT 1,
    fecha_creacion TEXT    NOT NULL DEFAULT (datetime('now')),
    fecha_actualizacion TEXT
);

CREATE INDEX IF NOT EXISTS ix_productos_codigo    ON productos(codigo);
CREATE INDEX IF NOT EXISTS ix_productos_nombre    ON productos(nombre);
CREATE INDEX IF NOT EXISTS ix_productos_activo    ON productos(activo);
CREATE INDEX IF NOT EXISTS ix_proveedores_nombre  ON proveedores(nombre);
CREATE INDEX IF NOT EXISTS ix_proveedores_activo  ON proveedores(activo);
