from django.core.management.base import BaseCommand

from apps.outbox.consumers import EVENT_TYPES, consume_once, run_forever


class Command(BaseCommand):
    """DOC 5 §8, Roadmap Этап 3 п.8-9, Этап 4 п.11. Blocking RabbitMQ consumer
    process: drains ApplicationSubmitted/ApplicationApproved/
    ApplicationRejected/ScoringCompleted and dispatches each to its
    registered handler (apps.outbox.consumers), e.g. the loan-issuance saga
    on ApplicationApproved, or ApplyScoringResultUseCase on ScoringCompleted
    (published by the external scoring_service, not by this process). Run as
    its own long-lived process (docker-compose's `saga-worker` service) —
    separate from the Celery/Redis worker, since this consumes from
    RabbitMQ, not Celery's own broker (DOC 5 §8.3: RabbitMQ is for Saga
    commands, kept apart from Celery's existing Redis broker)."""

    help = "Consume domain events from the broker and dispatch them to registered handlers."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process at most one message per event type, then exit (used by tests/CI smoke checks).",
        )
        parser.add_argument("--timeout", type=float, default=1.0)

    def handle(self, *args, **options) -> None:
        if options["once"]:
            for event_type in EVENT_TYPES:
                consume_once(event_type, timeout=options["timeout"])
            return
        run_forever(poll_timeout=options["timeout"])
