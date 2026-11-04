-- Reference data for Factory Sherlock.
-- Idempotent: every statement uses INSERT ... ON DUPLICATE KEY UPDATE keyed on
-- the natural unique code, so re-running the seed never duplicates rows.
-- Users are created by backend/app/seed.py because their password hashes are
-- generated at seed time from SEED_DEMO_PASSWORD.

INSERT INTO products (code, name, description) VALUES
  ('STEEL-SHAFT',   'Steel shaft 20 mm',   'Ground steel drive shaft, 20.00 mm nominal diameter, 150 mm length'),
  ('METAL-BRACKET', 'Metal bracket',       'Pressed steel mounting bracket with two 8 mm holes at 50 mm pitch'),
  ('GEAR',          'Spur gear 60 mm',     'Hobbed spur gear, 60.00 mm outer diameter, 12.00 mm bore')
ON DUPLICATE KEY UPDATE name = VALUES(name), description = VALUES(description);

INSERT INTO product_specifications (product_id, characteristic, target_value, tolerance, unit)
SELECT p.id, s.characteristic, s.target_value, s.tolerance, 'mm'
FROM products p
JOIN (
  SELECT 'STEEL-SHAFT'   AS code, 'diameter'       AS characteristic, 20.000  AS target_value, 0.100 AS tolerance UNION ALL
  SELECT 'STEEL-SHAFT',           'length',                           150.000,                 0.500           UNION ALL
  SELECT 'METAL-BRACKET',         'hole_position',                    50.000,                  0.200           UNION ALL
  SELECT 'METAL-BRACKET',         'thickness',                        5.000,                   0.100           UNION ALL
  SELECT 'GEAR',                  'outer_diameter',                   60.000,                  0.150           UNION ALL
  SELECT 'GEAR',                  'bore_diameter',                    12.000,                  0.050
) s ON s.code = p.code
ON DUPLICATE KEY UPDATE target_value = VALUES(target_value), tolerance = VALUES(tolerance);

INSERT INTO machines (code, name, status) VALUES
  ('CNC-01', 'CNC Machine 01', 'IDLE'),
  ('CNC-02', 'CNC Machine 02', 'IDLE'),
  ('CNC-03', 'CNC Machine 03', 'IDLE')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO defect_types (code, name, description) VALUES
  ('OVERSIZE_DIAMETER',       'Oversized diameter',      'Measured diameter above the upper tolerance limit'),
  ('UNDERSIZE_DIAMETER',      'Undersized diameter',     'Measured diameter below the lower tolerance limit'),
  ('HOLE_POSITION_DEVIATION', 'Hole position deviation', 'Hole pitch outside tolerance'),
  ('DIMENSIONAL_DEVIATION',   'Dimensional deviation',   'Any other linear dimension outside tolerance'),
  ('SURFACE_DAMAGE',          'Surface damage',          'Visible scoring, inclusion, or tearing attributed to material')
ON DUPLICATE KEY UPDATE name = VALUES(name), description = VALUES(description);

INSERT INTO material_lots (lot_number, material_name, supplier, quantity_received, status, received_at) VALUES
  ('L201', 'Steel bar stock 4140',  'Northline Steel',   500.00, 'AVAILABLE', '2026-10-20 08:00:00'),
  ('L202', 'Steel bar stock 4140',  'Northline Steel',   500.00, 'AVAILABLE', '2026-10-24 08:00:00'),
  ('L203', 'Steel bar stock 4140',  'Harbor Metals',     450.00, 'AVAILABLE', '2026-10-28 08:00:00'),
  ('L301', 'Sheet steel 3 mm',      'Harbor Metals',     800.00, 'AVAILABLE', '2026-10-21 08:00:00'),
  ('L302', 'Sheet steel 3 mm',      'Harbor Metals',     800.00, 'AVAILABLE', '2026-10-27 08:00:00'),
  ('L303', 'Sheet steel 3 mm',      'Lakeside Supply',   600.00, 'AVAILABLE', '2026-10-30 08:00:00'),
  ('L401', 'Alloy gear blank 8620', 'Lakeside Supply',   300.00, 'AVAILABLE', '2026-10-22 08:00:00'),
  ('L402', 'Alloy gear blank 8620', 'Lakeside Supply',   300.00, 'AVAILABLE', '2026-10-26 08:00:00'),
  ('L403', 'Alloy gear blank 8620', 'Northline Steel',   250.00, 'AVAILABLE', '2026-10-29 08:00:00')
ON DUPLICATE KEY UPDATE material_name = VALUES(material_name), supplier = VALUES(supplier);
