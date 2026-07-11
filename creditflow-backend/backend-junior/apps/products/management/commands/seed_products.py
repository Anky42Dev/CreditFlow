from django.core.management.base import BaseCommand

from apps.products.models import CreditProduct

PRODUCTS = [
    {
        "name": "Потребительский",
        "slug": "consumer",
        "description": "Кредит на любые цели без залога и поручителей.",
        "min_amount": "10000.00",
        "max_amount": "500000.00",
        "interest_rate": "18.50",
        "min_term_months": 3,
        "max_term_months": 36,
        "is_active": True,
    },
    {
        "name": "Экспресс-кредит",
        "slug": "express",
        "description": "Быстрое решение по небольшим суммам.",
        "min_amount": "5000.00",
        "max_amount": "100000.00",
        "interest_rate": "24.90",
        "min_term_months": 1,
        "max_term_months": 12,
        "is_active": True,
    },
    {
        "name": "Крупный кредит",
        "slug": "large-loan",
        "description": "Кредит на крупные покупки и ремонт.",
        "min_amount": "200000.00",
        "max_amount": "2000000.00",
        "interest_rate": "15.00",
        "min_term_months": 12,
        "max_term_months": 60,
        "is_active": True,
    },
    {
        "name": "Архивный продукт",
        "slug": "archived",
        "description": "Снят с продажи, оставлен для истории заявок.",
        "min_amount": "10000.00",
        "max_amount": "300000.00",
        "interest_rate": "22.00",
        "min_term_months": 3,
        "max_term_months": 24,
        "is_active": False,
    },
]


class Command(BaseCommand):
    help = "Seeds the database with sample credit products (idempotent, keyed by slug)."

    def handle(self, *args, **options):
        created_count = 0
        for data in PRODUCTS:
            _, created = CreditProduct.objects.update_or_create(
                slug=data["slug"], defaults=data
            )
            created_count += int(created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(PRODUCTS)} credit products ({created_count} created)."
            )
        )
