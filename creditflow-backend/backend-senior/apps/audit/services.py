from django.db import connection

# DOC 5 §14, Roadmap Этап 5 п.14: both partitioned-by-month tables (see
# apps/audit/migrations/0002_partition_by_month.py,
# apps/lending/migrations/0003_partition_by_month.py). Each also has a
# DEFAULT partition as a safety net, so a missed/late run of this degrades to
# "rows land in the unindexed-by-month catch-all" rather than failing inserts.
PARTITIONED_TABLES = ["audit_logs", "transactions"]

CREATE_MONTH_PARTITIONS_SQL = """
DO $$
DECLARE
    start_month date := date_trunc('month', now())::date;
    i int;
    part_start date;
    part_end date;
    part_name text;
BEGIN
    FOR i IN 0..{months_ahead} LOOP
        part_start := (start_month + (i || ' month')::interval)::date;
        part_end := (part_start + interval '1 month')::date;
        part_name := '{table}_' || to_char(part_start, 'YYYY_MM');
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF {table} FOR VALUES FROM (%L) TO (%L)',
            part_name, part_start, part_end
        );
    END LOOP;
END $$;
"""


def create_future_partitions(months_ahead: int = 3) -> list[str]:
    """Idempotently creates the next N months' partitions (from the current
    month) for every table in PARTITIONED_TABLES, so inserts always land in a
    proper monthly partition instead of falling through to the DEFAULT
    catch-all. Safe to re-run any time (CREATE TABLE IF NOT EXISTS). Shared
    by apps.audit.management.commands.create_future_partitions (manual/CI
    invocation) and apps.audit.tasks.create_future_partitions (Celery Beat,
    see config/settings.py CELERY_BEAT_SCHEDULE).

    Returns the list of table names processed.
    """
    if months_ahead < 0:
        raise ValueError("months_ahead must be >= 0")

    with connection.cursor() as cursor:
        for table in PARTITIONED_TABLES:
            cursor.execute(
                CREATE_MONTH_PARTITIONS_SQL.format(months_ahead=months_ahead, table=table)
            )
    return PARTITIONED_TABLES
