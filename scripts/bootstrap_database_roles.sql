\set ON_ERROR_STOP on

\if :{?DBNAME}
\else
\echo 'Connect to the intended ChangeOps RDS database before running this script.'
\quit
\endif

SELECT format('CREATE ROLE %I LOGIN', 'changeops_schema_owner')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'changeops_schema_owner')
\gexec

SELECT format('CREATE ROLE %I LOGIN', 'changeops_runtime')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'changeops_runtime')
\gexec

\echo 'Enter the migration secret password. Input is masked by psql.'
\password changeops_schema_owner
\echo 'Enter the distinct runtime secret password. Input is masked by psql.'
\password changeops_runtime

REVOKE CREATE ON DATABASE changeops FROM PUBLIC;
GRANT CONNECT ON DATABASE changeops TO changeops_schema_owner, changeops_runtime;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO changeops_schema_owner;
GRANT USAGE, CREATE ON SCHEMA public TO changeops_schema_owner;
GRANT USAGE ON SCHEMA public TO changeops_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE changeops_schema_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO changeops_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE changeops_schema_owner IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO changeops_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE changeops_schema_owner IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO changeops_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO changeops_runtime;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO changeops_runtime;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO changeops_runtime;

REVOKE CREATE ON DATABASE changeops FROM changeops_runtime;
REVOKE CREATE ON SCHEMA public FROM changeops_runtime;
