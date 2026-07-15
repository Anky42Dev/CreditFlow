"""DOC 5 §7, Roadmap Этап 4: standalone configuration for the scoring
service. Deliberately does not import Django/`decouple` — this service has
its own dependency set and release cycle (DOC 5 §7.1) and must run without
the Django project installed.

`EVENT_BROKER_URL` uses the same env var name as config.settings.EVENT_BROKER_URL
(backend-senior) so both processes point at the same RabbitMQ instance in
docker-compose.
"""

import os

EVENT_BROKER_URL = os.environ.get("EVENT_BROKER_URL", "memory://")

# Mirrors apps.applications.services.SCORE_APPROVED_THRESHOLD/
# SCORE_MANUAL_REVIEW_THRESHOLD (backend-senior) — kept as an independent
# copy on purpose (DOC 5 §7.1: scoring_service has its own release cycle),
# not imported across the process boundary.
SCORE_APPROVED_THRESHOLD = int(os.environ.get("SCORE_APPROVED_THRESHOLD", "700"))
SCORE_MANUAL_REVIEW_THRESHOLD = int(
    os.environ.get("SCORE_MANUAL_REVIEW_THRESHOLD", "500")
)
