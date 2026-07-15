class ReplicaRouter:
    """DOC 5 §14, Roadmap Этап 5 п.14: registers the 'replica' database alias
    for use by heavy reports/admin analytics on the audit log.

    `db_for_read` deliberately never redirects reads itself — routing every
    AuditLog read to 'replica' (by app_label alone) would silently apply to
    ordinary request-flow code too (e.g. a service reading back the entry it
    just wrote to build a response), which would return stale/missing data
    under real replication lag. That's not what DOC 5 §14 asks for — it's
    specifically "тяжёлые отчёты/админ-аналитика" (heavy reports/admin
    analytics), not audit reads in general. The one place that *is* that
    analytics path (apps.audit.views.AuditLogViewSet) opts in explicitly via
    `.using("replica")`, which always wins over any router decision — so
    this router's job is limited to allow_relation/allow_migrate, keeping
    'replica' a normal, fully-migrated alias.

    settings.DATABASES['replica'] defaults to the same connection as
    'default' when REPLICA_DB_HOST isn't set (see config/settings.py) — a
    safe no-op locally/in CI, not a real replica. Its 'TEST': {'MIRROR':
    'default'} avoids creating a second physical test database — see
    apps.audit.tests.AuditLogApiTests for why reading via 'replica' inside a
    test still needs TransactionTestCase (MIRROR shares the DB, not the
    transaction: default's TestCase wraps each alias in its own atomic
    block, so an uncommitted 'default' write is invisible to a separate
    'replica' connection until it's actually committed).
    """

    def db_for_read(self, model, **hints):
        return None

    def db_for_write(self, model, **hints):
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
