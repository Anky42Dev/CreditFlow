"""DOC 5 §16, Roadmap Этап 8 п.22: load test for the submit-application
path (AC-2..AC-5's happy path): register -> login -> create a DRAFT
application -> submit it.

Requires at least one active CreditProduct to already exist (GET
/api/v1/credit-products is fetched once per simulated user in on_start
and the run aborts with a clear error if none are found) — create one via
Django admin/shell before running, e.g.:

    python manage.py shell -c "
    from apps.products.models import CreditProduct
    CreditProduct.objects.create(
        name='Load Test Product', slug='load-test',
        min_amount=10000, max_amount=500000, interest_rate=15,
        min_term_months=6, max_term_months=36, is_active=True,
    )"

Run (against dev compose):
    locust -f tests/load/locustfile.py --host http://localhost:8000

Run (against docker-compose.prod, through nginx; self-signed cert handled
in on_start below):
    locust -f tests/load/locustfile.py --host https://localhost
"""

import random
import uuid

from locust import HttpUser, between, task


class ApplicantUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # docker-compose.prod's nginx serves a self-signed cert
        # (deploy/nginx/gen-cert.sh) — fine for this load test, not for
        # anything that should validate a real chain.
        self.client.verify = False

        self.email = f"loadtest-{uuid.uuid4().hex[:12]}@example.com"
        self.password = "LoadTest12345!"

        register = self.client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password},
            name="/api/v1/auth/register",
        )
        if register.status_code != 201:
            raise RuntimeError(f"register failed: {register.status_code} {register.text}")

        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password},
            name="/api/v1/auth/login",
        )
        access = login.json().get("access")
        if not access:
            raise RuntimeError(f"login failed: {login.status_code} {login.text}")
        self.client.headers.update({"Authorization": f"Bearer {access}"})

        products = self.client.get(
            "/api/v1/credit-products", name="/api/v1/credit-products"
        ).json()
        results = products.get("results", products) if isinstance(products, dict) else products
        if not results:
            raise RuntimeError(
                "No active credit products found — seed one before running "
                "the load test (see module docstring)."
            )
        self.product = results[0]

    @task
    def submit_application_flow(self):
        min_amount = float(self.product["min_amount"])
        max_amount = float(self.product["max_amount"])
        min_term = int(self.product["min_term_months"])
        max_term = int(self.product["max_term_months"])

        create = self.client.post(
            "/api/v1/credit-applications",
            json={
                "product": self.product["id"],
                # CreditApplication.amount is DecimalField(decimal_places=2)
                # (apps/applications/models.py) — round() dodges a 400 from
                # DRF rejecting float-precision noise from random.uniform().
                "amount": round(random.uniform(min_amount, max_amount), 2),
                "term_months": random.randint(min_term, max_term),
                "purpose": "load-test",
            },
            name="/api/v1/credit-applications [create]",
        )
        if create.status_code != 201:
            return

        application_id = create.json()["id"]
        self.client.post(
            f"/api/v1/credit-applications/{application_id}/submit",
            name="/api/v1/credit-applications/[id]/submit",
        )
