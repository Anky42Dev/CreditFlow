from django.core.management.base import BaseCommand

from apps.audit.services import create_future_partitions


class Command(BaseCommand):
    """DOC 5 §14, Roadmap Этап 5 п.14: manual/CI entry point for
    apps.audit.services.create_future_partitions — see that function's
    docstring. Also runs monthly via Celery Beat
    (apps.audit.tasks.create_future_partitions, config/settings.py
    CELERY_BEAT_SCHEDULE)."""

    help = "Create upcoming monthly partitions for audit_logs and transactions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--months-ahead", type=int, default=3,
            help="How many months ahead (from the current month) to provision. Default: 3.",
        )

    def handle(self, *args, **options):
        tables = create_future_partitions(months_ahead=options["months_ahead"])
        for table in tables:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Ensured partitions for {table} up to {options['months_ahead']} month(s) ahead."
                )
            )
