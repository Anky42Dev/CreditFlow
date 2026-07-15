# DOC 5 §10.5: append-only enforcement at the DB-privilege level. The
# project runs a single Postgres role that owns audit_logs (it created the
# table in migrations), and Postgres table owners always bypass GRANT/REVOKE
# restrictions on their own tables — so a REVOKE UPDATE/DELETE is a no-op
# here. A BEFORE UPDATE/DELETE trigger enforces it instead, and works
# regardless of ownership. Row-level triggers defined on a partitioned
# parent (Postgres 11+) automatically cascade to every existing and future
# partition, so one trigger on audit_logs is enough — no per-partition setup
# needed (see apps.audit.management.commands.create_future_partitions for
# how new partitions get created).
from django.db import migrations

CREATE_TRIGGER = """
CREATE FUNCTION audit_logs_deny_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only: % is not permitted', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION audit_logs_deny_mutation();
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs;
DROP FUNCTION IF EXISTS audit_logs_deny_mutation();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_partition_by_month"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_TRIGGER, reverse_sql=DROP_TRIGGER),
    ]
