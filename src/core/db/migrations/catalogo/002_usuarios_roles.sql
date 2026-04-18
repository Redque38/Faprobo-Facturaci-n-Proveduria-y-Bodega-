-- 002_usuarios_roles.sql — Gestión de usuarios del sistema y roles.

CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE,
    descripcion TEXT    NOT NULL DEFAULT '',
    activo      INTEGER NOT NULL DEFAULT 1,
    fecha_creacion TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS usuarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT    NOT NULL UNIQUE,
    nombre       TEXT    NOT NULL,
    apellido     TEXT    NOT NULL DEFAULT '',
    password_hash TEXT   NOT NULL,
    rol_id       INTEGER NOT NULL REFERENCES roles(id),
    activo       INTEGER NOT NULL DEFAULT 1,
    fecha_creacion     TEXT NOT NULL DEFAULT (datetime('now')),
    fecha_actualizacion TEXT
);

CREATE INDEX IF NOT EXISTS ix_usuarios_username ON usuarios(username);
CREATE INDEX IF NOT EXISTS ix_usuarios_rol      ON usuarios(rol_id);
CREATE INDEX IF NOT EXISTS ix_usuarios_activo   ON usuarios(activo);

-- Roles por defecto
INSERT OR IGNORE INTO roles (id, nombre, descripcion) VALUES
    (1, 'Administrador', 'Acceso total al sistema'),
    (2, 'Cajero',        'Gestión de facturación y ventas'),
    (3, 'Bodeguero',     'Gestión de productos e inventario'),
    (4, 'Supervisor',    'Acceso a reportes y consultas');

-- Usuario administrador por defecto  (password: admin123 → sha256)
INSERT OR IGNORE INTO usuarios (id, username, nombre, apellido, password_hash, rol_id)
VALUES (1, 'admin', 'Administrador', 'Sistema',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 1);
