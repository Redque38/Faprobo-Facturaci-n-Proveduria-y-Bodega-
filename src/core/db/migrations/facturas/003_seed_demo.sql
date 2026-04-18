-- 003_seed_demo.sql — Datos de demostración para Facturación.
-- Esta migración se ejecuta una sola vez (migrations_runner la registra en schema_version).

INSERT INTO facturas (tipo, entidad_id, subtotal, descuento, impuesto, total, estado, es_electronica, sync_duckdb, fecha_creacion)
VALUES
    ('venta',  1, 10000.00, 0.00,   1300.00, 11300.00, 'pagada',    0, 0, datetime('now', '-2 days')),
    ('venta',  2, 25000.00, 2500.00, 2925.00, 25425.00, 'pendiente', 0, 0, datetime('now', '-1 day')),
    ('compra', 1, 50000.00, 0.00,   6500.00, 56500.00, 'pagada',    0, 0, datetime('now'));

INSERT INTO factura_lineas (factura_id, producto_id, descripcion, cantidad, precio_unitario, descuento_linea, total_linea)
VALUES
    (1, 1, 'Laptop Dell XPS 13',          1,  10000.00, 0.00,    10000.00),
    (2, 2, 'Monitor LG 27" 4K IPS',       2,  12500.00, 2500.00, 22500.00),
    (3, 3, 'Teclado Mecánico Keychron K2', 10, 5000.00,  0.00,    50000.00);
