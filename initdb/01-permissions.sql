-- MySQL runs the files in this folder once, the first time the database starts
-- (same idea as the Week 7 MySqlDatabaseDocker sample).
--
-- The app creates its own tables on start-up (db.create_all() in app/__init__.py).
-- The app's MySQL user (DB_USER in .env) is created automatically with full rights
-- on the `evote` database.
--
-- PLACEHOLDER (WS-D, R07): replace full rights with least-privilege roles, GRANTs
-- and VIEWs (Week 7 lecture slides 13-21, Week 7 lab slide 8, Week 7 init-roles-users.sql).
SELECT 'initdb: no extra permissions yet (R07)';
