  -- R07: database permissions are applied after the tables exist, not here.
  -- This folder runs on first boot, before the app creates its tables.
  -- See db/permissions.sql and apply_permissions.py (run by the init service).
  SELECT 'initdb: permissions are applied by the init service (R07)';