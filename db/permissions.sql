-- R07: least-privilege database access (Week 7: roles, GRANT, views)
-- Applied by apply_permissions.py as the admin user, after the tables exist.
-- @APP_USER@ is replaced with DB_USER from .env.

-- this cleans up the earlier draft roles and does nothing if they dont exist
DROP ROLE IF EXISTS 'evote_data_rw', 'evote_audit_append';

-- this creates a view listing electors without their encrypted personal columns, for staff screens.
CREATE OR REPLACE VIEW evote.electors_staff_view AS
SELECT e.id, e.enrolment_no, e.enrolled, (e.user_id IS NOT NULL) AS has_account,
       d.name AS division, d.state
FROM evote.electors e
JOIN evote.divisions d ON d.id = e.division_id;

-- this creates the roles, then resets them so this file always describes the final state
CREATE ROLE IF NOT EXISTS 'evote_app_role', 'evote_audit_role';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'evote_app_role';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'evote_audit_role';

-- this makes it so the app gets only SELECT INSERT UPDATE on the tables it uses, and no DROP ALTER DELETE
GRANT SELECT, INSERT, UPDATE ON evote.users TO 'evote_app_role';
GRANT SELECT, INSERT, UPDATE ON evote.electors TO 'evote_app_role';
GRANT SELECT, INSERT, UPDATE ON evote.divisions TO 'evote_app_role';
GRANT SELECT, INSERT, UPDATE ON evote.elections TO 'evote_app_role';
GRANT SELECT, INSERT, UPDATE ON evote.candidates TO 'evote_app_role';
GRANT SELECT, INSERT, UPDATE ON evote.candidate_proposals TO 'evote_app_role';
GRANT SELECT, INSERT, UPDATE ON evote.participation TO 'evote_app_role';
GRANT SELECT, INSERT, UPDATE ON evote.ballots TO 'evote_app_role';
GRANT SELECT, INSERT, UPDATE ON evote.results TO 'evote_app_role';
GRANT SELECT ON evote.electors_staff_view TO 'evote_app_role';

-- this is the only table the app may delete from (auth.py removes MFA enrolment rows)
GRANT SELECT, INSERT, UPDATE, DELETE ON evote.mfa_enrollments TO 'evote_app_role';

-- makes it so we can only SELECT and INSERT on audit_log
GRANT SELECT, INSERT ON evote.audit_log TO 'evote_audit_role';

-- when the app is used, remove what the MySQL image gave it then assign the roles
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '@APP_USER@'@'%';
GRANT 'evote_app_role', 'evote_audit_role' TO '@APP_USER@'@'%';
SET DEFAULT ROLE 'evote_app_role', 'evote_audit_role' TO '@APP_USER@'@'%';

